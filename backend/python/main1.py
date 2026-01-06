from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from firebase_config import db
from firebase_admin import firestore

app = FastAPI(
    title="Student Notes CRUD API",
    description="CRUD + Versioning + Analytics (No ML, No File Upload)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Section(BaseModel):
    heading: str
    points: list[str]

class User(BaseModel):
    name: str
    email: str
class Note(BaseModel):
    user_id: str
    title: str
    content: str
    summary: str | None = ""
    entities: dict | None = {}
    introduction: str | None = ""
    sections: list[Section] | None = []
    conclusion: str | None = ""


class Analytics(BaseModel):
    user_id: str
    note_id: str
    action: str

@app.post("/users")
def create_user(user: User):
    doc_ref = db.collection("users").document()
    doc_ref.set({
        "name": user.name,
        "email": user.email,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "lastLogin": firestore.SERVER_TIMESTAMP
    })
    return {"status": "User created", "userId": doc_ref.id}


@app.post("/notes")
def create_note(note: Note):
    doc_ref = db.collection("notes").document()
    
    
    doc_ref.set({
        "userId": note.user_id,
        "title": note.title,
        "content": note.content,
        "summary": note.summary,
        "entities": note.entities,
        "structuredNotes": {
            "title": note.title,
            "introduction": note.introduction,
            "sections": [s.dict() for s in note.sections],
            "conclusion": note.conclusion
        },
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "version": 1
    })

    
    db.collection("analytics").add({
        "userId": note.user_id,
        "noteId": doc_ref.id,
        "action": "created",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {"status": "Note created", "noteId": doc_ref.id}

@app.get("/notes/{note_id}")
def read_note(note_id: str):
    doc = db.collection("notes").document(note_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Note not found")

    note = doc.to_dict()

 
    db.collection("analytics").add({
        "userId": note["userId"],
        "noteId": note_id,
        "action": "viewed",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return note

@app.put("/notes/{note_id}")
def update_note(note_id: str, note: Note):
    doc_ref = db.collection("notes").document(note_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Note not found")

    old = doc.to_dict()


    doc_ref.collection("versions").add({
        "title": old.get("title", ""),
        "content": old.get("content", ""),
        "summary": old.get("summary", ""),
        "entities": old.get("entities", {}),
        "structuredNotes": old.get("structuredNotes", {}),
        "versionNumber": old.get("version", 1),
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    doc_ref.update({
        "title": note.title,
        "content": note.content,
        "summary": note.summary,
        "entities": note.entities,
        "structuredNotes": {
            "title": note.title,
            "introduction": note.introduction,
            "sections": [s.dict() for s in note.sections],
            "conclusion": note.conclusion
        },
        "version": old.get("version", 1) + 1,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

  
    db.collection("analytics").add({
        "userId": note.user_id,
        "noteId": note_id,
        "action": "updated",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    return {"status": "Note updated", "noteId": note_id}

@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    doc_ref = db.collection("notes").document(note_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Note not found")

    doc_ref.delete()
    return {"status": "Note deleted"}

@app.post("/analytics")
def log_analytics(data: Analytics):
    db.collection("analytics").add({
        "userId": data.user_id,
        "noteId": data.note_id,
        "action": data.action,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    return {"status": "Logged"}


@app.get("/")
def root():
    return {"status": "CRUD backend running"}
