"""
Database Schemas for Dynamic Learning Path Recommendation System

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

# Users
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    role: Literal["student", "instructor", "admin"] = Field("student")
    interests: List[str] = Field(default_factory=list)
    goals: Optional[str] = Field(None)
    preferences: Dict[str, Any] = Field(default_factory=dict, description="pace, timePerWeek, learningStyle, etc.")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Catalog
class CourseModule(BaseModel):
    title: str
    description: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    masteryThreshold: int = Field(70, ge=0, le=100)
    estMinutes: int = Field(30, ge=1)

class Course(BaseModel):
    title: str
    description: str
    topics: List[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    prerequisites: List[str] = Field(default_factory=list)
    syllabus: List[CourseModule] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)  # resource ids (string)
    rating: float = 4.5

class Resource(BaseModel):
    type: Literal["video", "article", "practice"]
    topic: str
    url: str
    title: str
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    lengthMinutes: Optional[int] = None

# Assessments
class Question(BaseModel):
    id: str
    prompt: str
    options: List[str]
    answerIndex: int
    topic: str
    difficulty: int = Field(1, ge=1, le=5)

class Assessment(BaseModel):
    kind: Literal["placement", "topic"] = "placement"
    topic: Optional[str] = None
    title: str
    questions: List[Question]
    difficulty: Optional[str] = None
    timeEstimate: Optional[int] = None

class Attempt(BaseModel):
    userId: str
    assessmentId: Optional[str] = None
    kind: Literal["placement", "topic"] = "placement"
    responses: List[int]
    score: int
    topicMasteryDeltas: Dict[str, int] = Field(default_factory=dict)
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None

# Paths and recommendations
class PathItem(BaseModel):
    type: Literal["course", "module", "resource"]
    id: str
    status: Literal["pending", "in_progress", "completed"] = "pending"
    masteryTarget: Optional[int] = 70
    order: int = 0

class Path(BaseModel):
    userId: str
    items: List[PathItem] = Field(default_factory=list)
    lastUpdatedBy: Literal["system", "user"] = "system"
    rationaleLog: List[str] = Field(default_factory=list)

class RecommendationItem(BaseModel):
    type: Literal["course", "resource", "assessment"]
    id: str
    score: float = 0.0
    explanation: Optional[str] = None

class Recommendation(BaseModel):
    userId: str
    items: List[RecommendationItem]
    createdAt: Optional[datetime] = None

class Interaction(BaseModel):
    userId: str
    contentId: str
    type: Literal["view", "complete", "skip"]
    duration: Optional[int] = None
    device: Optional[str] = None
    timestamp: Optional[datetime] = None
