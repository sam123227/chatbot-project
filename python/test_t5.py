from transformers import T5Tokenizer, T5ForConditionalGeneration

# -------------------------------
# Load Model & Tokenizer
# -------------------------------
model_name = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

# -------------------------------
# Chunking Function
# -------------------------------
def chunk_text(text, tokenizer, max_tokens=450, overlap=50):
    tokens = tokenizer.encode(text)
    chunks = []

    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunks.append(chunk_text)
        start = end - overlap

    return chunks

# -------------------------------
# Summarize Single Chunk
# -------------------------------
def summarize_chunk(chunk, tokenizer, model):
    input_text = "summarize: " + chunk

    inputs = tokenizer.encode(
        input_text,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )

    outputs = model.generate(
        inputs,
        max_length=120,
        min_length=40,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True,
        no_repeat_ngram_size=3,
        repetition_penalty=2.0
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# -------------------------------
# Full Text Summarization
# -------------------------------
def summarize_text(text, tokenizer, model):
    chunks = chunk_text(text, tokenizer)
    chunk_summaries = []

    print(f"Total chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks, start=1):
        print(f"Summarizing chunk {i}/{len(chunks)}...")
        summary = summarize_chunk(chunk, tokenizer, model)
        chunk_summaries.append(summary)

    combined_summary = " ".join(chunk_summaries)

    # Final compression summary
    input_text = "summarize: " + combined_summary

    inputs = tokenizer.encode(
        input_text,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )

    outputs = model.generate(
        inputs,
        max_length=150,
        min_length=60,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True,
        no_repeat_ngram_size=3
    )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# -------------------------------
# TEST INPUT (replace later with file/OCR text)
# -------------------------------
text = """
Pollution is one of the most serious environmental problems facing the world today.
It affects air, water, and soil and causes serious health issues.
Pollution contributes to climate change, biodiversity loss, and ecosystem damage.
Governments and individuals must work together to reduce pollution.
""" * 20  # simulate long text

# -------------------------------
# Run Summarizer
# -------------------------------
final_summary = summarize_text(text, tokenizer, model)

print("\nFINAL SUMMARY:\n")
print(final_summary)
