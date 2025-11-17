import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import User, Course, Resource, Path, Recommendation

app = FastAPI(title="Dynamic Learning Path Recommendation System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Dynamic Learning Path API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# ---------- Public Catalog ----------
@app.get("/catalog/courses")
async def list_courses(search: Optional[str] = None, topic: Optional[str] = None, difficulty: Optional[str] = None):
    q = {}
    if search:
        q["title"] = {"$regex": search, "$options": "i"}
    if topic:
        q["topics"] = {"$in": [topic]}
    if difficulty:
        q["difficulty"] = difficulty
    try:
        docs = get_documents("course", q, limit=50)
        # Convert ObjectId to string
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog/courses/{course_id}")
async def get_course(course_id: str):
    try:
        from bson import ObjectId
        doc = db["course"].find_one({"_id": ObjectId(course_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Course not found")
        doc["_id"] = str(doc["_id"]) 
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog/resources")
async def list_resources(topic: Optional[str] = None, rtype: Optional[str] = None):
    q = {}
    if topic:
        q["topic"] = topic
    if rtype:
        q["type"] = rtype
    try:
        docs = get_documents("resource", q, limit=50)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Minimal Auth (placeholder, no passwords) ----------
class SignupPayload(BaseModel):
    name: str
    email: str

@app.post("/auth/signup")
async def signup(payload: SignupPayload):
    """Simple signup that creates a user if not exists (no password for demo)."""
    user = User(name=payload.name, email=payload.email, role="student")
    try:
        # Upsert by email for demo simplicity
        existing = db["user"].find_one({"email": user.email}) if db else None
        if existing:
            existing["_id"] = str(existing["_id"])
            return {"user": existing, "status": "exists"}
        _id = create_document("user", user)
        doc = db["user"].find_one({"_id": __import__('bson').ObjectId(_id)})
        doc["_id"] = str(doc["_id"]) 
        return {"user": doc, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Path & Recommendations (v1 rule-based placeholder) ----------
@app.get("/path")
async def get_path(userId: str):
    try:
        doc = db["path"].find_one({"userId": userId})
        if not doc:
            return {"userId": userId, "items": [], "lastUpdatedBy": "system", "rationaleLog": []}
        doc["_id"] = str(doc["_id"]) 
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InitPathPayload(BaseModel):
    userId: str
    goals: Optional[str] = None
    interests: List[str] = []

@app.post("/path/init")
async def init_path(payload: InitPathPayload):
    """Create a simple initial path based on interests/goals using available courses."""
    try:
        q = {}
        if payload.interests:
            q["topics"] = {"$in": payload.interests}
        courses = list(db["course"].find(q).limit(5))
        items = []
        order = 0
        for c in courses:
            items.append({"type": "course", "id": str(c["_id"]), "status": "pending", "masteryTarget": 70, "order": order})
            order += 1
        path_doc = {"userId": payload.userId, "items": items, "lastUpdatedBy": "system", "rationaleLog": [
            f"Initial path created at {datetime.now(timezone.utc).isoformat()} based on interests {payload.interests} and goals '{payload.goals}'."
        ], "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        db["path"].find_one_and_update({"userId": payload.userId}, {"$set": path_doc}, upsert=True)
        saved = db["path"].find_one({"userId": payload.userId})
        saved["_id"] = str(saved["_id"]) 
        return saved
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations")
async def get_recommendations(userId: str):
    """Return simple recommendations: top resources matching user's interests or recent gaps."""
    try:
        user = db["user"].find_one({"_id": __import__('bson').ObjectId(userId)}) if len(userId) == 24 else db["user"].find_one({"email": userId})
        interests = user.get("interests", []) if user else []
        q = {"topic": {"$in": interests}} if interests else {}
        resources = list(db["resource"].find(q).limit(6))
        items = [{"type": "resource", "id": str(r["_id"]), "score": 0.8, "explanation": f"Matches your interest in {r.get('topic')}"} for r in resources]
        return {"userId": userId, "items": items, "createdAt": datetime.now(timezone.utc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Bootstrap sample data for demo ----------
@app.post("/bootstrap")
async def bootstrap():
    try:
        if db["course"].count_documents({}) == 0:
            sample_courses = [
                Course(
                    title="Intro to Data Structures",
                    description="Learn arrays, linked lists, stacks, and queues.",
                    topics=["arrays", "linked lists", "stacks", "queues"],
                    difficulty="beginner",
                    prerequisites=[],
                    syllabus=[],
                    resources=[],
                    rating=4.7,
                ).model_dump(),
                Course(
                    title="Algorithms Essentials",
                    description="Sorting, searching, and complexity basics.",
                    topics=["sorting", "searching", "complexity"],
                    difficulty="intermediate",
                    prerequisites=["Intro to Data Structures"],
                    syllabus=[],
                    resources=[],
                    rating=4.6,
                ).model_dump(),
            ]
            for c in sample_courses:
                c["created_at"] = datetime.now(timezone.utc)
                c["updated_at"] = datetime.now(timezone.utc)
                db["course"].insert_one(c)
        if db["resource"].count_documents({}) == 0:
            sample_resources = [
                Resource(type="video", topic="arrays", url="https://www.youtube.com/watch?v=8hly31xKli0", title="Arrays Crash Course").model_dump(),
                Resource(type="article", topic="sorting", url="https://www.khanacademy.org/computing/computer-science/algorithms", title="Sorting Basics").model_dump(),
                Resource(type="practice", topic="linked lists", url="https://leetcode.com/tag/linked-list/", title="Linked List Practice").model_dump(),
            ]
            for r in sample_resources:
                r["created_at"] = datetime.now(timezone.utc)
                r["updated_at"] = datetime.now(timezone.utc)
                db["resource"].insert_one(r)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
