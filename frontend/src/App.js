import React, { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [entities, setEntities] = useState({});
  const [structuredNotes, setStructuredNotes] = useState(null);
  const [showText, setShowText] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [showNER, setShowNER] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedNotes, setSavedNotes] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [username, setUsername] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!file) return alert("Please select a file");
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    setText("");
    setSummary("");
    setEntities({});
    setStructuredNotes(null);
    setShowText(false);
    setShowSummary(false);
    setShowNER(false);
    setShowNotes(false);
    try {
      const res = await fetch("http://localhost:8000/extract-file", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setText(data.raw_text || "");
      setSummary(data.summary || "");
      setEntities(data.entities || {});
      setStructuredNotes(data.structured_notes || null);
    } catch {
      alert("Backend not running or CORS issue");
    }
    setLoading(false);
  };

  const handleSaveNote = async () => {
    if (!structuredNotes) return alert("No notes to save");
    try {
      await fetch("http://localhost:8001/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: username,
          title: structuredNotes?.title || "Untitled",
          content: text.trim(),
          summary: summary ? summary.trim() : "",
          entities: entities || {},
          introduction: structuredNotes?.introduction || "",
          sections: structuredNotes?.sections || [],
          conclusion: structuredNotes?.conclusion || "",
        }),
      });
      alert("Saved successfully!");
    } catch (err) {
      alert("Failed to save note to Firebase");
    }
  };

  const handleViewHistory = async () => {
    try {
      const res = await fetch(`http://localhost:8001/notes/user/${username}`);
      const data = await res.json();
      setSavedNotes(data);
      setShowHistory(true);
    } catch (err) {
      alert("Failed to load notes");
    }
  };

  const handleEdit = (note, noteId) => {
    setEditingNote(noteId);
    setEditTitle(note.title || "");
    setEditContent(note.content || "");
  };

  const handleSaveEdit = async (noteId) => {
    try {
      await fetch(`http://localhost:8001/notes/${noteId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: username,
          title: editTitle,
          content: editContent,
          summary: "",
          entities: {},
          introduction: "",
          sections: [],
          conclusion: "",
        }),
      });
      alert("Updated successfully!");
      setEditingNote(null);
      handleViewHistory();
    } catch (err) {
      alert("Failed to update note");
    }
  };

  const handleDelete = async (noteId) => {
    if (!window.confirm("Are you sure?")) return;
    try {
      await fetch(`http://localhost:8001/notes/${noteId}`, {
        method: "DELETE",
      });
      alert("Deleted successfully!");
      handleViewHistory();
    } catch (err) {
      alert("Failed to delete note");
    }
  };

  // ✅ Login screen
  if (!isLoggedIn) {
    return (
      <div className="container" style={{ textAlign: "center", marginTop: "100px" }}>
        <h1>Document Processing & Notes Service</h1>
        <h3>Enter your name to continue</h3>
        <input
          type="text"
          placeholder="Enter your name"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{
            padding: "10px", borderRadius: "8px",
            border: "1px solid #d1d5db", marginRight: "10px", width: "250px",
          }}
        />
        <button
          onClick={() => { if (username.trim()) setIsLoggedIn(true); }}
          style={{
            backgroundColor: "#2563eb", color: "white",
            padding: "10px 20px", borderRadius: "8px",
            border: "none", cursor: "pointer",
          }}
        >
          Continue
        </button>
      </div>
    );
  }

  return (
    <div className="container">

      {/* ✅ Header with truly centered title */}
      <div style={{
        position: "relative", display: "flex", alignItems: "center",
        justifyContent: "flex-end", marginBottom: "30px",
      }}>
        <h1 style={{
          position: "absolute", left: "50%", transform: "translateX(-50%)",
          margin: 0, whiteSpace: "nowrap",
        }}>
          Document Processing & Notes Service
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ color: "#6b7280", fontSize: "14px" }}>
            👤 {username}
          </span>
          <button
            onClick={handleViewHistory}
            style={{
              backgroundColor: "#6366f1", color: "white",
              padding: "8px 16px", borderRadius: "8px",
              border: "none", cursor: "pointer",
            }}
          >
            View Saved Notes
          </button>
          <button
            onClick={() => setIsLoggedIn(false)}
            style={{
              backgroundColor: "#ef4444", color: "white",
              padding: "8px 16px", borderRadius: "8px",
              border: "none", cursor: "pointer",
            }}
          >
            Logout
          </button>
        </div>
      </div>

      <div className="upload-box">
        <input type="file" accept=".pdf,.docx" onChange={handleFileChange} />
        <button onClick={handleUpload}>
          {loading ? "Processing..." : "Upload & Process"}
        </button>
      </div>

      {loading && <p className="loading">Processing document…</p>}

      {(text || summary || Object.keys(entities).length > 0) && (
        <div className="toggle-group">
          {text && (
            <button onClick={() => setShowText(!showText)}>
              {showText ? "Hide Extracted Text" : "Show Extracted Text"}
            </button>
          )}
          {summary && (
            <button onClick={() => setShowSummary(!showSummary)}>
              {showSummary ? "Hide Summary" : "Show Summary"}
            </button>
          )}
          {Object.keys(entities).length > 0 && (
            <button onClick={() => setShowNER(!showNER)}>
              {showNER ? "Hide NER" : "Show NER"}
            </button>
          )}
          {structuredNotes && !showNotes && (
            <button onClick={() => setShowNotes(true)}>Show Notes</button>
          )}
        </div>
      )}

      {showText && (
        <div className="section">
          <h3>Extracted Text</h3>
          <textarea value={text} readOnly />
        </div>
      )}

      {showSummary && (
        <div className="section">
          <h3>Summary</h3>
          <p>{summary}</p>
        </div>
      )}

      {showNER && (
        <div className="section">
          <h3>Named Entity Recognition</h3>
          {Object.entries(entities).map(([label, vals]) => (
            <p key={label}>
              <strong>{label}:</strong> {vals.join(", ")}
            </p>
          ))}
        </div>
      )}

      {structuredNotes && showNotes && (
        <div className="section notes">
          <h2>{structuredNotes.title}</h2>
          <h3>Introduction</h3>
          <p>{structuredNotes.introduction}</p>
          {structuredNotes.sections.map((sec, idx) => (
            <div key={idx} className="note-section">
              <h3>{sec.heading}</h3>
              <ul>
                {sec.points.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          ))}
          <h3>Conclusion</h3>
          <p>{structuredNotes.conclusion}</p>
          <button
            onClick={handleSaveNote}
            style={{
              marginTop: "20px", backgroundColor: "#2563eb",
              color: "white", padding: "10px 20px",
              borderRadius: "8px", border: "none", cursor: "pointer",
            }}
          >
            Save
          </button>
        </div>
      )}

      {showHistory && (
        <div className="section">
          <div style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", marginBottom: "16px",
          }}>
            <h2>Saved Notes</h2>
            <button
              onClick={() => setShowHistory(false)}
              style={{
                backgroundColor: "#ef4444", color: "white",
                padding: "6px 12px", borderRadius: "6px",
                border: "none", cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>

          {savedNotes.length === 0 && <p>No saved notes found.</p>}

          {savedNotes.map((item) => (
            <div key={item.id} style={{
              border: "1px solid #e5e7eb",
              borderRadius: "8px", padding: "16px", marginBottom: "12px",
            }}>
              {editingNote === item.id ? (
                <div>
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    style={{
                      width: "100%", marginBottom: "8px",
                      padding: "8px", borderRadius: "6px",
                      border: "1px solid #d1d5db",
                    }}
                  />
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={4}
                    style={{
                      width: "100%", marginBottom: "8px",
                      padding: "8px", borderRadius: "6px",
                      border: "1px solid #d1d5db",
                    }}
                  />
                  <button
                    onClick={() => handleSaveEdit(item.id)}
                    style={{
                      backgroundColor: "#22c55e", color: "white",
                      padding: "6px 12px", borderRadius: "6px",
                      border: "none", cursor: "pointer", marginRight: "8px",
                    }}
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingNote(null)}
                    style={{
                      backgroundColor: "#6b7280", color: "white",
                      padding: "6px 12px", borderRadius: "6px",
                      border: "none", cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div>
                  <h3 style={{ marginBottom: "8px" }}>
                    {item.structuredNotes?.title || item.title}
                  </h3>

                  {item.structuredNotes?.introduction && (
                    <div style={{ marginBottom: "8px" }}>
                      <strong>Introduction</strong>
                      <p style={{ color: "#374151", fontSize: "14px" }}>
                        {item.structuredNotes.introduction}
                      </p>
                    </div>
                  )}

                  {item.structuredNotes?.sections?.map((sec, idx) => (
                    <div key={idx} style={{ marginBottom: "8px" }}>
                      <strong>{sec.heading}</strong>
                      <ul style={{ marginTop: "4px" }}>
                        {sec.points.map((p, i) => (
                          <li key={i} style={{ fontSize: "14px", color: "#374151" }}>
                            {p}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}

                  {item.structuredNotes?.conclusion && (
                    <div style={{ marginBottom: "8px" }}>
                      <strong>Conclusion</strong>
                      <p style={{ color: "#374151", fontSize: "14px" }}>
                        {item.structuredNotes.conclusion}
                      </p>
                    </div>
                  )}

                  <p style={{ color: "#9ca3af", fontSize: "12px", marginBottom: "12px" }}>
                    Version: {item.version || 1}
                  </p>

                  <button
                    onClick={() => handleEdit(item, item.id)}
                    style={{
                      backgroundColor: "#f59e0b", color: "white",
                      padding: "6px 12px", borderRadius: "6px",
                      border: "none", cursor: "pointer", marginRight: "8px",
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    style={{
                      backgroundColor: "#ef4444", color: "white",
                      padding: "6px 12px", borderRadius: "6px",
                      border: "none", cursor: "pointer",
                    }}
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;