from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MaterialStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    needs_review = "needs_review"
    ready = "ready"
    archived = "archived"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    needs_review = "needs_review"
    ready = "ready"
    failed = "failed"


class TaskType(str, Enum):
    flashcard = "flashcard"
    listen_choice = "listen_choice"
    match_choice = "match_choice"
    speaking_prompt = "speaking_prompt"
    parent_coaching = "parent_coaching"


class DifficultyBand(str, Enum):
    recognition = "recognition"
    repeat = "repeat"
    comprehension = "comprehension"
    output = "output"


class ReviewTaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class SpeakingAttemptStatus(str, Enum):
    queued = "queued"
    recording_uploaded = "recording_uploaded"
    transcribing = "transcribing"
    scored = "scored"
    failed = "failed"


class ChildProfile(BaseModel):
    id: str
    name: str
    avatar_url: str = ""
    age: int
    level: str
    learning_goal: str
    preferred_review_duration_minutes: int
    parent_notes: str = ""


class ChildProfileCreate(BaseModel):
    name: str
    age: int
    level: str
    learning_goal: str
    preferred_review_duration_minutes: int = 10
    parent_notes: str = ""


class CourseMaterial(BaseModel):
    id: str
    child_id: str
    teacher_name: str
    lesson_date: date
    title: str
    topic: str = ""
    status: MaterialStatus
    source_images: list[str] = Field(default_factory=list)
    pdf_url: str = ""
    ocr_text: str = ""
    tags: list[str] = Field(default_factory=list)


class CourseMaterialCreate(BaseModel):
    child_id: str
    teacher_name: str
    lesson_date: date
    title: str
    topic: str = ""
    source_images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MaterialParseJob(BaseModel):
    id: str
    material_id: str
    status: JobStatus
    confidence_summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: Optional[datetime] = None
    draft_title: str = ""
    draft_topic: str = ""
    draft_vocabulary: list[str] = Field(default_factory=list)
    draft_sentences: list[str] = Field(default_factory=list)


class MaterialParseConfirmRequest(BaseModel):
    draft_title: Optional[str] = None
    draft_topic: Optional[str] = None
    draft_vocabulary: Optional[list[str]] = None
    draft_sentences: Optional[list[str]] = None


class VocabularyItem(BaseModel):
    id: str
    knowledge_pack_id: str
    word: str
    phonics: str = ""
    meaning_cn: str = ""
    image_url: str = ""
    audio_url: str = ""
    example_sentence: str = ""


class SentencePattern(BaseModel):
    id: str
    knowledge_pack_id: str
    sentence: str
    meaning_cn: str = ""
    usage_type: str = ""
    audio_url: str = ""


class KnowledgePack(BaseModel):
    id: str
    material_id: str
    topic: str
    difficulty_band: DifficultyBand
    lesson_summary: str
    review_recommendation: str
    vocabulary_items: list[VocabularyItem] = Field(default_factory=list)
    sentence_patterns: list[SentencePattern] = Field(default_factory=list)


class ReviewTask(BaseModel):
    id: str
    child_id: str
    material_id: str
    task_type: TaskType
    difficulty: str
    content_json: dict[str, Any] = Field(default_factory=dict)
    due_date: datetime
    status: ReviewTaskStatus


class PracticeSession(BaseModel):
    id: str
    child_id: str
    review_task_ids: list[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: float = 0
    weak_points: list[str] = Field(default_factory=list)


class PracticeSessionCreate(BaseModel):
    child_id: str
    review_task_ids: list[str]
    score: float = 0.0
    weak_points: list[str] = Field(default_factory=list)


class SpeakingAttempt(BaseModel):
    id: str
    child_id: str
    material_id: str
    prompt_text: str
    audio_url: str = ""
    transcript: str = ""
    pronunciation_score: Optional[float] = None
    feedback: str = ""
    status: SpeakingAttemptStatus


class WeeklyReport(BaseModel):
    id: str
    child_id: str
    week_start: date
    week_end: date
    completed_sessions: int = 0
    reviewed_words: int = 0
    speaking_attempts: int = 0
    weak_items: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class MaterialCreateResponse(BaseModel):
    material: CourseMaterial
    job: MaterialParseJob


class KnowledgePackDetailResponse(BaseModel):
    material: CourseMaterial
    knowledge_pack: KnowledgePack


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTask]


class WeeklyReportResponse(BaseModel):
    report: WeeklyReport
