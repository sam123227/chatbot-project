from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from transformers import T5Tokenizer, T5ForConditionalGeneration
from io import BytesIO
import torch
import re
import pdfplumber
from docx import Document

app = FastAPI(
    title="Student Notes API",
    description="Upload PDF/DOCX → Clean Study Notes with Summary & NER",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
MODEL_NAME = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None


def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

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

def chunk_text(text: str, max_words: int = 200):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i+max_words])

def summarize_text(text: str) -> str:
    chunks = list(chunk_text(text)) if len(text.split()) > 200 else [text]
    summaries = []
    with torch.no_grad():
        for chunk in chunks:
            inputs = tokenizer(
                "summarize: " + chunk,
                return_tensors="pt",
                truncation=True,
                max_length=512
            ).to(device)
            outputs = model.generate(
                inputs["input_ids"],
                max_length=350,  
                min_length=120,
                num_beams=4,
                early_stopping=True
            )
            summaries.append(tokenizer.decode(outputs[0], skip_special_tokens=True))
    return " ".join(summaries)


def extract_entities(text: str):
    if not nlp:
        return {}
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        if len(ent.text) > 2:
            entities.setdefault(ent.label_, set()).add(ent.text)
    return {k: list(v) for k, v in entities.items()}

def generate_final_notes(summary: str):
    """
    Generates general structured notes suitable for any text:
    - Introduction
    - Highlights / Key Points
    - Important Details / Examples
    - Challenges / Limitations
    - Conclusion
    """
  
    sentences = re.split(r'(?<=[.!?])\s+', summary.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    clean_sentences = []
    for s in sentences:
        s = s[0].upper() + s[1:]
        if s[-1] not in ".!?":
            s += "."
        if any(x in s.lower() for x in ["please contact us", "for more information", "visit our website"]):
            continue
        clean_sentences.append(s)
    sentences = clean_sentences

    title = "Notes"
    if sentences and nlp:
        doc = nlp(sentences[0])
        for token in doc:
            if token.pos_ in  ["PROPN"]:
                title = token.text.title()
                break

    introduction = sentences[0] if sentences else ""
    conclusion = sentences[-1] if len(sentences) > 1 else introduction

    highlights = []
    details = []
    challenges = []

    for s in sentences[1:]:  
        lower_s = s.lower()
        if any(k in lower_s for k in ["risk", "limitation", "challenge", "issue", "problem", "drawback"]):
            challenges.append(s)
        elif any(k in lower_s for k in ["for example", "such as", "including", "like"]):
            details.append(s)
        else:
            highlights.append(s)

    highlights = highlights[:5]
    details = details[:5]
    challenges = challenges[:5]

    formatted_sections = []
    if highlights:
        formatted_sections.append({"heading": "Highlights", "points": highlights})
    if details:
        formatted_sections.append({"heading": "Important Details / Examples", "points": details})
    if challenges:
        formatted_sections.append({"heading": "Challenges / Limitations", "points": challenges})

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
    structured_notes = generate_final_notes(summary)  

    return {
        "raw_text": raw_text,
        "summary": summary,
        "entities": entities,
        "structured_notes": structured_notes
    }

@app.get("/")
def root():
    return {"status": "Backend running"}

