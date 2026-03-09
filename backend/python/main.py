from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
from io import BytesIO
import re
import pdfplumber
from docx import Document

app = FastAPI(
    title="Student Notes API",
    description="Upload PDF/DOCX and Clean Study Notes with Summary & NER",
    version="7.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

summarizer = pipeline(
    "summarization",
    model="sshleifer/distilbart-cnn-12-6",
    device=-1
)

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None


def clean_text(text: str) -> str:
    text = re.sub(r'\b(technical|market|marketing|financial|legal|operational|project management)\s+risks?:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[A-Z][A-Z\s]{3,}:\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_text_from_pdf(upload_file: UploadFile) -> str:
    pdf_bytes = BytesIO(upload_file.file.read())
    text = ""
    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.strip()


def extract_text_from_docx(upload_file: UploadFile) -> str:
    upload_file.file.seek(0)
    doc = Document(upload_file.file)
    return " ".join([p.text for p in doc.paragraphs]).strip()


def chunk_text(text: str, max_words: int = 400):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])


def summarize_text(text: str) -> str:
    original_text = text
    word_count = len(text.split())
    chunks = list(chunk_text(text)) if word_count > 400 else [text]

    summaries = []
    for chunk in chunks:
        if len(chunk.split()) < 30:
            summaries.append(chunk)
            continue
        try:
            result = summarizer(
                chunk,
                max_length=250,
                min_length=80,
                do_sample=False,
                truncation=True
            )
            summaries.append(result[0]["summary_text"])
        except Exception:
            summaries.append(chunk)

    combined = " ".join(summaries)
    sentences = re.split(r'(?<=[.!?])\s+', combined.strip())

    seen = set()
    unique = []
    for s in sentences:
        key = s.lower().strip()
        if key not in seen and len(key) > 10:
            seen.add(key)
            unique.append(s)

    cleaned = []
    for s in unique:
        s = s.strip()
        s = re.sub(r'\s+([.!?,])', r'\1', s)
        s = s[0].upper() + s[1:]
        if s[-1] not in ".!?":
            s += "."
        if any(x in s.lower() for x in ["please contact", "for more information",
                                          "visit www", "call us"]):
            continue
        cleaned.append(s)

    
    if cleaned:
        first_words = cleaned[0].split()
        if first_words[0].lower() in ["is", "was", "are", "were", "has", "have", "its", "it"]:
            if nlp:
                doc = nlp(original_text[:300])
                for ent in doc.ents:
                    if ent.label_ in ["ORG", "GPE", "PERSON"] and len(ent.text) > 2:
                        cleaned[0] = ent.text + " " + cleaned[0][0].lower() + cleaned[0][1:]
                        break

    return " ".join(cleaned)


def extract_entities(text: str):
    if not nlp:
        return {}

    doc = nlp(text)
    entities = {}

    allowed_labels = {
        "ORG", "PRODUCT", "GPE", "PERSON", "WORK_OF_ART",
        "LAW", "MONEY", "DATE", "EVENT", "FAC", "NORP",
        "QUANTITY", "PERCENT", "TIME", "LOC"
    }

    for ent in doc.ents:
        clean_ent = re.sub(r'^[Tt]he\s+', '', ent.text.strip())
        if clean_ent.count("(") != clean_ent.count(")"):
            continue
        if len(clean_ent) <= 2:
            continue
        if clean_ent.lower() in {"the", "a", "an", "this", "that", "it", "etc", "many"}:
            continue
        if re.match(r'^\d+$', clean_ent):
            continue
        if re.search(r'\b(of|the|and|a|an)$', clean_ent.lower()):
            continue
        if ent.label_ not in allowed_labels:
            continue
        entities.setdefault(ent.label_, set()).add(clean_ent)

    
    years = re.findall(r'\b(?:19|20)\d{2}\b', text)
    if years:
        entities.setdefault("DATE", set()).update(years)

    
    figures = re.findall(r'\b\d+[\.,]?\d*\s*(?:million|billion|thousand|%)\b', text, re.IGNORECASE)
    if figures:
        entities.setdefault("QUANTITY", set()).update([f.strip() for f in figures])

    
    known_products = {"iphone", "ipad", "apple watch", "airpods", "mac",
                      "macbook", "app store", "android", "windows", "playstation"}
    if "ORG" in entities:
        misclassified = {e for e in entities["ORG"] if e.lower() in known_products}
        entities["ORG"] -= misclassified
        if misclassified:
            entities.setdefault("PRODUCT", set()).update(misclassified)

    
    false_people = {"buddha", "lumbini", "nepal", "app store"}
    if "PERSON" in entities:
        entities["PERSON"] = {e for e in entities["PERSON"]
                              if e.lower() not in false_people}

    
    false_dates = {"annually", "monthly", "weekly", "daily", "yearly"}
    if "DATE" in entities:
        entities["DATE"] = {e for e in entities["DATE"]
                            if e.lower() not in false_dates}

    
    if "GPE" in entities and "LOC" in entities:
        entities["GPE"].update(entities.pop("LOC"))
    elif "LOC" in entities:
        entities["GPE"] = entities.pop("LOC")

    
    important_terms = set()
    for chunk in doc.noun_chunks:
        term = chunk.text.strip()
        term = re.sub(r'^(a|an|the|this|that|these|those)\s+', '', term, flags=re.IGNORECASE)
        term = term.strip()
        words = term.split()
        if len(words) >= 2 and len(term) > 5:
            if not any(w in term.lower() for w in ["which", "that", "when", "where",
                                                     "who", "how", "what", "its", "their"]):
                if any(w[0].isupper() for w in words) or len(words) >= 3:
                    important_terms.add(term.title())

    if important_terms:
        existing = set()
        for v in entities.values():
            existing.update([x.lower() for x in v])
        filtered = {t for t in important_terms if t.lower() not in existing}
        if filtered:
            entities.setdefault("TERMS", set()).update(filtered)

    
    if "TERMS" in entities:
        existing = set()
        for k, v in entities.items():
            if k != "TERMS":
                existing.update([x.lower() for x in v])
        entities["TERMS"] = {t for t in entities["TERMS"]
                             if t.lower() not in existing}

    label_map = {
        "ORG":         "Organizations",
        "PRODUCT":     "Products & Tools",
        "GPE":         "Locations",
        "FAC":         "Facilities & Places",
        "PERSON":      "People",
        "NORP":        "Nationalities & Groups",
        "WORK_OF_ART": "Referenced Works",
        "EVENT":       "Events",
        "LAW":         "Legal References",
        "MONEY":       "Financial Figures",
        "QUANTITY":    "Figures & Statistics",
        "PERCENT":     "Percentages",
        "DATE":        "Dates & Timeframes",
        "TIME":        "Time References",
        "TERMS":       "Key Terms & Concepts",
    }

    result = {label_map.get(k, k): sorted(list(v)) for k, v in entities.items()}
    return {k: v for k, v in result.items() if v}


def detect_doc_type(text: str) -> str:
    text = text.lower()
    scores = {
        "technical":   sum(1 for k in ["software", "hardware", "api", "system", "framework",
                                        "engine", "tool", "network", "security", "vr", "ar",
                                        "unity", "unreal", "firewall", "platform", "database"] if k in text),
        "geography":   sum(1 for k in ["country", "capital", "government", "president", "minister",
                                        "republic", "democratic", "nation", "region", "located",
                                        "border", "province", "saarc", "bimstec"] if k in text),
        "business":    sum(1 for k in ["market", "revenue", "profit", "budget", "cost", "financial",
                                        "investment", "competition", "economy", "growth", "sales",
                                        "strategy", "customer", "brand", "company", "founded"] if k in text),
        "science":     sum(1 for k in ["research", "experiment", "hypothesis", "theory", "data",
                                        "analysis", "result", "method", "study", "evidence",
                                        "variable", "sample", "observation", "equation"] if k in text),
        "history":     sum(1 for k in ["war", "century", "ancient", "empire", "civilization",
                                        "revolution", "independence", "historical", "period",
                                        "era", "battle", "treaty", "kingdom", "dynasty"] if k in text),
        "health":      sum(1 for k in ["disease", "treatment", "patient", "health", "medicine",
                                        "symptom", "hospital", "clinical", "medical", "therapy",
                                        "diagnosis", "doctor", "drug", "vaccine", "insulin"] if k in text),
        "education":   sum(1 for k in ["student", "teacher", "school", "university", "learning",
                                        "curriculum", "education", "course", "exam",
                                        "grade", "degree", "academic", "classroom"] if k in text),
        "environment": sum(1 for k in ["climate", "environment", "pollution", "carbon", "emission",
                                        "ecosystem", "biodiversity", "renewable", "energy",
                                        "deforestation", "wildlife", "sustainable"] if k in text),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def get_section_map(doc_type: str):
    maps = {
        "technical": [
            (["purpose", "goal", "objective", "aim", "overview"],                          "Overview"),
            (["require", "hardware", "software", "tool", "api", "system",
              "platform", "engine", "framework", "vr", "ar", "network", "firewall"],       "Technical Requirements"),
            (["risk", "challenge", "issue", "problem", "limitation",
              "threat", "fail", "breach", "exceed"],                                       "Risks & Challenges"),
            (["for example", "such as", "including", "specifically"],                      "Supporting Details"),
        ],
        "geography": [
            (["government", "minister", "president", "parliament", "constitution",
              "republic", "democratic", "institution", "court", "ministry",
              "member", "saarc", "bimstec", "united nations", "organization"],             "Government & Institutions"),
            (["economy", "tourism", "trade", "development", "bank",
              "infrastructure", "growth", "industry", "heritage", "attract"],              "Economy & Tourism"),
            (["founded", "established", "movement", "agreement", "independence",
              "milestone", "adopted", "signed", "historically"],                           "Historical Milestones"),
            (["for example", "such as", "including", "specifically"],                      "Key Facts"),
        ],
        "business": [
            (["founded", "history", "headquarter", "started", "established",
              "ceo", "company", "corporation", "valuable", "world"],                       "Company Overview"),
            (["revenue", "profit", "budget", "cost", "investment", "financial",
              "expense", "funding", "market", "sales", "billion", "million",
              "generates", "earning"],                                                      "Financial Overview"),
            (["risk", "challenge", "competition", "issue", "problem",
              "limitation", "threat", "concern", "compete"],                               "Risks & Challenges"),
            (["product", "service", "launch", "iphone", "ipad", "software",
              "hardware", "app", "platform", "popular", "sells", "designs"],              "Products & Services"),
        ],
        "science": [
            (["method", "experiment", "procedure", "approach", "technique",
              "process", "analysis", "hypothesis", "equation"],                            "Methodology"),
            (["result", "finding", "outcome", "evidence", "data",
              "shows", "proves", "indicates", "demonstrates"],                             "Findings & Results"),
            (["limitation", "challenge", "issue", "problem",
              "however", "despite", "drawback", "error"],                                  "Limitations"),
            (["for example", "such as", "including", "specifically"],                      "Examples & Details"),
        ],
        "history": [
            (["cause", "reason", "led to", "because", "due to",
              "triggered", "background", "rise"],                                           "Causes & Background"),
            (["war", "battle", "movement", "revolution", "independence",
              "founded", "established", "signed", "adopted", "event",
              "invasion", "attack", "defeat"],                                              "Key Events"),
            (["impact", "effect", "consequence", "result", "changed",
              "transformed", "influenced", "aftermath", "formation"],                      "Impact & Consequences"),
            (["for example", "such as", "including", "specifically"],                      "Supporting Details"),
        ],
        "health": [
            (["cause", "reason", "risk factor", "due to", "because",
              "triggered", "linked to", "leads to", "obesity", "immune"],                  "Causes & Risk Factors"),
            (["symptom", "sign", "effect", "affect", "pain", "condition",
              "suffer", "experience", "complication", "urination",
              "thirst", "fatigue", "vision"],                                               "Symptoms & Effects"),
            (["treatment", "therapy", "medicine", "cure", "prevent",
              "manage", "hospital", "drug", "vaccine", "insulin",
              "medication", "exercise", "diet", "diagnosis"],                              "Treatment & Prevention"),
            (["for example", "such as", "including", "specifically"],                      "Supporting Details"),
        ],
        "education": [
            (["goal", "objective", "purpose", "aim", "mission",
              "curriculum", "program", "course", "degree"],                                "Educational Objectives"),
            (["method", "approach", "technique", "style", "strategy",
              "learning", "teaching", "instruction", "activity", "ai", "tool"],           "Teaching & Learning"),
            (["challenge", "issue", "problem", "limitation", "barrier",
              "difficulty", "concern", "gap", "dishonesty", "divide"],                     "Challenges"),
            (["for example", "such as", "including", "specifically"],                      "Supporting Details"),
        ],
        "environment": [
            (["cause", "reason", "due to", "because", "triggered",
              "emission", "pollution", "fossil", "deforestation"],                         "Causes & Factors"),
            (["effect", "impact", "consequence", "result", "change",
              "affect", "damage", "harm", "threat", "melting",
              "rising", "disaster", "flood", "drought"],                                   "Effects & Impact"),
            (["solution", "renewable", "sustainable", "reduce", "prevent",
              "protect", "conserve", "clean", "green", "policy",
              "agreement", "solar", "wind"],                                                "Solutions & Initiatives"),
            (["for example", "such as", "including", "specifically"],                      "Supporting Details"),
        ],
        "general": [
            (["important", "key", "main", "major", "significant",
              "primary", "essential", "notable", "critical"],                              "Key Points"),
            (["for example", "such as", "including", "specifically",
              "for instance", "like"],                                                      "Supporting Details"),
            (["however", "but", "challenge", "issue", "problem",
              "limitation", "risk", "concern", "difficult"],                               "Challenges"),
        ],
    }
    return maps.get(doc_type, maps["general"])


def generate_final_notes(summary: str, original_text: str = ""):
    summary = re.sub(r'\b(technical|market|marketing|financial|legal|operational|project management)\s+risks?:\s*', '', summary, flags=re.IGNORECASE)
    summary = re.sub(r'\b[A-Z][A-Z\s]{3,}:\s*', '', summary)
    summary = re.sub(r'\s+', ' ', summary).strip()

    sentences = re.split(r'(?<=[.!?])\s+', summary.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    seen = set()
    unique_sentences = []
    for s in sentences:
        key = s.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_sentences.append(s)
    sentences = unique_sentences

    clean_sentences = []
    for s in sentences:
        s = s[0].upper() + s[1:]
        if s[-1] not in ".!?":
            s += "."
        if any(x in s.lower() for x in ["please contact", "for more information",
                                          "visit www", "call us"]):
            continue
        clean_sentences.append(s)
    sentences = clean_sentences

    
    if sentences:
        first_words = sentences[0].split()
        if first_words[0].lower() in ["is", "was", "are", "were", "has", "have", "its", "it"]:
            if nlp and original_text:
                doc = nlp(original_text[:300])
                for ent in doc.ents:
                    if ent.label_ in ["ORG", "GPE", "PERSON"] and len(ent.text) > 2:
                        sentences[0] = ent.text + " " + sentences[0][0].lower() + sentences[0][1:]
                        break

    if not sentences:
        return {"title": "Document Notes", "introduction": "", "sections": [], "conclusion": ""}


    title = "Document Notes"
    if nlp:
        doc = nlp(original_text[:300] if original_text else " ".join(sentences[:2]))
        for ent in doc.ents:
            if ent.label_ in ["ORG", "GPE", "PRODUCT", "PERSON", "EVENT"] and len(ent.text) > 3:
                title = ent.text.title() + " — Study Notes"
                break


    if title == "Document Notes" and sentences:
        topic_words = re.findall(r'\b[A-Z][a-z]{3,}\b', sentences[0])
        if topic_words:
            title = topic_words[0] + " — Study Notes"

    introduction = sentences[0]
    conclusion = sentences[-1] if len(sentences) > 1 else introduction
    if conclusion == introduction:
        conclusion = "Further study and analysis is recommended for a deeper understanding."

    doc_type = detect_doc_type(" ".join(sentences))
    section_map = get_section_map(doc_type)

    categories = {label: [] for _, label in section_map}

    for s in sentences[1:-1]:
        lower_s = s.lower()
        matched = False
        for keywords, label in section_map:
            if any(k in lower_s for k in keywords):
                categories[label].append(s)
                matched = True
                break
        if not matched:
            first_label = section_map[0][1]
            categories[first_label].append(s)

    formatted_sections = []
    for _, label in section_map:
        if categories[label]:
            formatted_sections.append({
                "heading": label,
                "points": categories[label][:5]
            })

    return {
        "title": title,
        "introduction": introduction,
        "sections": formatted_sections,
        "conclusion": conclusion
    }


@app.post("/extract-file")
async def extract_file(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file)
    elif filename.endswith(".docx"):
        raw_text = extract_text_from_docx(file)
    else:
        return {"error": "Only PDF and DOCX supported"}

    if not raw_text:
        return {"raw_text": "", "summary": "", "entities": {}, "structured_notes": {}}

    cleaned_text = clean_text(raw_text)
    summary = summarize_text(cleaned_text)
    entities = extract_entities(cleaned_text)
    structured_notes = generate_final_notes(summary, original_text=cleaned_text)

    return {
        "raw_text": raw_text,
        "summary": summary,
        "entities": entities,
        "structured_notes": structured_notes
    }


@app.get("/")
def root():
    return {"status": "Backend running"}