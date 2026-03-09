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
    setText(""); setSummary(""); setEntities({});
    setStructuredNotes(null);
    setShowText(false); setShowSummary(false);
    setShowNER(false); setShowNotes(false);
    try {
      const res = await fetch("http://localhost:8000/extract-file", {
        method: "POST", body: formData,
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
    } catch { alert("Failed to save note to Firebase"); }
  };

  const handleViewHistory = async () => {
    try {
      const res = await fetch(`http://localhost:8001/notes/user/${username}`);
      const data = await res.json();
      setSavedNotes(data);
      setShowHistory(true);
    } catch { alert("Failed to load notes"); }
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
          user_id: username, title: editTitle,
          content: editContent, summary: "",
          entities: {}, introduction: "",
          sections: [], conclusion: "",
        }),
      });
      alert("Updated successfully!");
      setEditingNote(null);
      handleViewHistory();
    } catch { alert("Failed to update note"); }
  };

  const handleDelete = async (noteId) => {
    if (!window.confirm("Are you sure?")) return;
    try {
      await fetch(`http://localhost:8001/notes/${noteId}`, { method: "DELETE" });
      alert("Deleted successfully!");
      handleViewHistory();
    } catch { alert("Failed to delete note"); }
  };

  if (!isLoggedIn) {
    return (
      <div className="login-wrapper">
        <div className="login-card">
          <span className="login-icon">📄</span>
          <h2 className="login-title">Document Processing & Notes Service</h2>
          <p className="login-subtitle">Upload any document. Get intelligent study notes.</p>
          <input
            className="login-input"
            type="text"
            placeholder="Enter your name to continue..."
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && username.trim()) setIsLoggedIn(true); }}
          />
          <button className="btn-continue" onClick={() => { if (username.trim()) setIsLoggedIn(true); }}>
            Continue →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <nav className="navbar">
        <span className="navbar-brand">📄 Notes Service</span>
        <div className="navbar-right">
          <div className="user-chip">
            <div className="user-avatar">{username[0]?.toUpperCase()}</div>
            {username}
          </div>
          <button className="btn-purple" onClick={handleViewHistory}>View Saved Notes</button>
          <button className="btn-red" onClick={() => setIsLoggedIn(false)}>Logout</button>
        </div>
      </nav>

      <div className="main-content">

        <div className="upload-card">
          <span className="upload-icon">📂</span>
          <p className="upload-title">Upload Your Document</p>
          <p className="upload-subtitle">Supports PDF and DOCX files</p>
          <div className="upload-row">
            <label className="btn-choose">
              {file ? file.name : "Choose File"}
              <input type="file" accept=".pdf,.docx" onChange={handleFileChange} style={{ display: "none" }} />
            </label>
            <button className="btn-upload" onClick={handleUpload}>
              {loading ? "Processing..." : "Upload & Process"}
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-bar">
            <div className="spinner"></div>
            Processing document with AI...
          </div>
        )}

        {(text || summary || Object.keys(entities).length > 0) && (
          <div className="toggle-group">
            {text && <button className="btn-toggle" onClick={() => setShowText(!showText)}>{showText ? "Hide" : "Show"} Extracted Text</button>}
            {summary && <button className="btn-toggle" onClick={() => setShowSummary(!showSummary)}>{showSummary ? "Hide" : "Show"} Summary</button>}
            {Object.keys(entities).length > 0 && <button className="btn-toggle" onClick={() => setShowNER(!showNER)}>{showNER ? "Hide" : "Show"} NER</button>}
            {structuredNotes && <button className="btn-toggle" onClick={() => setShowNotes(!showNotes)}>{showNotes ? "Hide" : "Show"} Notes</button>}
          </div>
        )}

        {showText && (
          <div className="section-card">
            <p className="section-heading">Extracted Text</p>
            <textarea className="extracted-textarea" value={text} readOnly />
          </div>
        )}

        {showSummary && (
          <div className="section-card">
            <p className="section-heading">Summary</p>
            <p className="section-text">{summary}</p>
          </div>
        )}

        {showNER && (
          <div className="section-card">
            <p className="section-heading">Named Entity Recognition</p>
            {Object.entries(entities).map(([label, vals]) => (
              <div className="ner-row" key={label}>
                <span className="ner-label">{label}</span>
                {vals.map((v, i) => <span className="ner-tag" key={i}>{v}</span>)}
              </div>
            ))}
          </div>
        )}

        {structuredNotes && showNotes && (
          <div className="section-card">
            <h2 className="notes-title">{structuredNotes.title}</h2>
            <div className="notes-section">
              <p className="notes-section-heading">Introduction</p>
              <p className="notes-intro">{structuredNotes.introduction}</p>
            </div>
            {structuredNotes.sections.map((sec, idx) => (
              <div className="notes-section" key={idx}>
                <p className="notes-section-heading">{sec.heading}</p>
                <ul className="notes-list">
                  {sec.points.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
            ))}
            <div className="notes-section">
              <p className="notes-section-heading">Conclusion</p>
              <p className="notes-intro">{structuredNotes.conclusion}</p>
            </div>
            <button className="btn-save" onClick={handleSaveNote}>Save Notes ✓</button>
          </div>
        )}

        {showHistory && (
          <div className="section-card">
            <div className="history-header">
              <h2 className="history-title">Saved Notes</h2>
              <button className="btn-close" onClick={() => setShowHistory(false)}>Close ✕</button>
            </div>
            {savedNotes.length === 0 && <p className="empty-state">No saved notes found.</p>}
            {savedNotes.map((item) => (
              <div className="saved-note-card" key={item.id}>
                {editingNote === item.id ? (
                  <div>
                    <input className="edit-input" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                    <textarea className="edit-textarea" value={editContent} onChange={(e) => setEditContent(e.target.value)} rows={4} />
                    <button className="btn-confirm" onClick={() => handleSaveEdit(item.id)}>Save</button>
                    <button className="btn-cancel" onClick={() => setEditingNote(null)}>Cancel</button>
                  </div>
                ) : (
                  <>
                    <p className="saved-note-title">{item.structuredNotes?.title || item.title}</p>
                    {item.structuredNotes?.introduction && (<><p className="saved-note-label">Introduction</p><p className="saved-note-text">{item.structuredNotes.introduction}</p></>)}
                    {item.structuredNotes?.sections?.map((sec, idx) => (
                      <div key={idx}>
                        <p className="saved-note-label">{sec.heading}</p>
                        <ul className="saved-note-list">{sec.points.map((p, i) => <li key={i}>{p}</li>)}</ul>
                      </div>
                    ))}
                    {item.structuredNotes?.conclusion && (<><p className="saved-note-label">Conclusion</p><p className="saved-note-text">{item.structuredNotes.conclusion}</p></>)}
                    <div className="saved-note-footer">
                      <span className="version-badge">v{item.version || 1}</span>
                      <div className="note-actions">
                        <button className="btn-edit" onClick={() => handleEdit(item, item.id)}>Edit</button>
                        <button className="btn-delete" onClick={() => handleDelete(item.id)}>Delete</button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;