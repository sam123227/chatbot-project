const express = require("express");
const cors = require("cors");
const fileUpload = require("express-fileupload");
const mammoth = require("mammoth");
const pdfParse = require("pdf-parse");

const app = express();
app.use(cors());
app.use(fileUpload());

function splitSentences(text) {
  return text
    .replace(/\n+/g, ". ")
    .replace(/\s+/g, " ")
    .split(/(?<=[.?!])\s+/)
    .map(s => s.trim())
    .filter(s => s.length > 20);
}

function wordFrequency(text) {
  const commonWords = [
    "the","i","is","am","a","an","and","or","of","to","in","on","for",
    "with","at","by","from","as","that","this","it","are","was","were",
    "he","she","they","you","him","her","their"
  ];

  const words = text
    .toLowerCase()
    .replace(/[^a-z\s]/g, "")
    .split(/\s+/);

  const freq = {};

  for (let word of words) {
    if (word && !commonWords.includes(word)) {
      freq[word] = (freq[word] || 0) + 1;
    }
  }

  return freq;
}

function scoreSentences(sentences, wordFreq) {
  const scores = {};

  sentences.forEach(sentence => {
    let score = 0;

    const words = sentence
      .toLowerCase()
      .replace(/[^a-z\s]/g, "")
      .split(" ");

    words.forEach(word => {
      if (wordFreq[word]) {
        score += wordFreq[word];
      }
    });

    scores[sentence] = score;
  });

  return scores;
}

function getSummary(sentenceScores, limit) {
  return Object.entries(sentenceScores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(item => item[0]);
}

app.post("/extract-file", async (req, res) => {
  try {
    if (!req.files || !req.files.file) {
      return res.status(400).json({ message: "No file uploaded" });
    }

    const uploadedFile = req.files.file;
    const ext = uploadedFile.name.split(".").pop().toLowerCase();
    let extractedText = "";

    if (ext === "docx") {
      const result = await mammoth.extractRawText({
        buffer: uploadedFile.data
      });
      extractedText = result.value;

    } else if (ext === "pdf") {
      const data = await pdfParse(uploadedFile.data);
      extractedText = data.text;

    } else {
      return res.status(400).json({ message: "Unsupported file type" });
    }

    const sentences = splitSentences(extractedText);
    const wordFreq = wordFrequency(extractedText);
    const sentenceScores = scoreSentences(sentences, wordFreq);
    const summarySize = Math.ceil(sentences.length * 0.5);
    const summary = getSummary(sentenceScores, summarySize);

    res.json({
      text: extractedText,
      summary
    });

  } catch (err) {
    console.error("File extraction error:", err);
    res.status(500).json({ message: "Extraction failed" });
  }
});

app.listen(8081, () => {
  console.log("Backend running on port 8081");
});
