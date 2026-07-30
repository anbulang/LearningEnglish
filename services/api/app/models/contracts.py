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
    failed = "failed"
    archived = "archived"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    needs_review = "needs_review"
    ready = "ready"
    failed = "failed"


class MediaGenerationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    partial = "partial"  # some assets ready, some failed (phonics dual-accent gen)
    ready = "ready"
    failed = "failed"


class PrimaryAccent(str, Enum):
    us = "us"
    uk = "uk"


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


class AuthStatus(str, Enum):
    authenticated = "authenticated"
    phone_binding_required = "phone_binding_required"


class ParentAccount(BaseModel):
    id: str
    display_name: str
    avatar_url: str = ""
    phone_number: str = ""
    phone_verified_at: Optional[datetime] = None
    wechat_union_id: str = ""
    wechat_open_id: str = ""
    created_at: datetime
    updated_at: datetime


class StoredAsset(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    bucket: str
    object_key: str
    content_type: str
    size_bytes: int
    url: str
    created_at: datetime


class ChildProfile(BaseModel):
    id: str
    parent_account_id: str
    name: str
    avatar_url: str = ""
    age: int
    level: str
    learning_goal: str
    preferred_review_duration_minutes: int
    parent_notes: str = ""
    accent: str = "us"  # "us" (American) | "uk" (British) — phonics audio accent


class ChildProfileCreate(BaseModel):
    name: str
    age: int
    level: str
    learning_goal: str
    preferred_review_duration_minutes: int = 10
    parent_notes: str = ""
    accent: str = "us"


class ChildProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    level: Optional[str] = None
    learning_goal: Optional[str] = None
    preferred_review_duration_minutes: Optional[int] = None
    parent_notes: Optional[str] = None
    accent: Optional[str] = None


class CourseMaterial(BaseModel):
    id: str
    child_id: str
    parse_job_id: str = ""
    teacher_name: str
    lesson_date: date
    title: str
    topic: str = ""
    status: MaterialStatus
    source_images: list[str] = Field(default_factory=list)
    source_image_keys: list[str] = Field(default_factory=list)
    normalized_image_keys: list[str] = Field(default_factory=list)
    pdf_url: str = ""
    pdf_key: str = ""
    file_size_bytes: int = 0
    uploaded_at: Optional[datetime] = None
    ocr_text: str = ""
    tags: list[str] = Field(default_factory=list)
    image_records: list["MaterialImageRecord"] = Field(default_factory=list)
    learning_assets: list["LearningAsset"] = Field(default_factory=list)


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
    draft_image_records: list["MaterialImageRecord"] = Field(default_factory=list)
    draft_learning_assets: list["LearningAsset"] = Field(default_factory=list)


class MaterialImageRecord(BaseModel):
    id: str
    page_index: int
    source_type: str = "gallery"
    original_filename: str = ""
    url: str = ""
    object_key: str = ""
    content_type: str = ""
    size_bytes: int = 0
    image_title: str = ""
    ocr_text: str = ""
    vocabulary: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


class SourceBoundingBox(BaseModel):
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0


class LearningAsset(BaseModel):
    id: str
    text: str
    kind: str
    translation: str = ""
    source_page_index: int = 1
    source_bbox: Optional[SourceBoundingBox] = None
    source_visual_description: str = ""
    pronunciation_text: str = ""
    image_prompt: str = ""
    difficulty: str = "easy"
    teaching_note: str = ""
    is_core: bool = True
    generated_image_status: MediaGenerationStatus = MediaGenerationStatus.pending
    generated_image_url: str = ""
    generated_image_object_key: str = ""
    generated_image_error: str = ""
    tts_us_status: MediaGenerationStatus = MediaGenerationStatus.pending
    tts_us_url: str = ""
    tts_us_object_key: str = ""
    tts_us_error: str = ""
    tts_uk_status: MediaGenerationStatus = MediaGenerationStatus.pending
    tts_uk_url: str = ""
    tts_uk_object_key: str = ""
    tts_uk_error: str = ""
    primary_accent: PrimaryAccent = PrimaryAccent.us


class MaterialParseConfirmRequest(BaseModel):
    draft_title: Optional[str] = None
    draft_topic: Optional[str] = None
    draft_vocabulary: Optional[list[str]] = None
    draft_sentences: Optional[list[str]] = None


class LearningAssetPrimaryAccentUpdate(BaseModel):
    primary_accent: PrimaryAccent


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


class PracticeTaskResult(BaseModel):
    task_id: str
    answer: str = ""  # listen_choice: picked word · flashcard: self-rate ("known"/"unknown")
    answers: list[str] = Field(default_factory=list)  # match_choice: chosen right per left, in left order


class PracticeSessionCreate(BaseModel):
    child_id: str
    review_task_ids: list[str]
    # When task_results is provided the server derives score + weak_points from the
    # child's actual answers (authoritative). score/weak_points are a legacy
    # fallback for callers that don't submit per-task answers.
    task_results: list[PracticeTaskResult] = Field(default_factory=list)
    score: float = 0.0
    weak_points: list[str] = Field(default_factory=list)


class SpeakingWordFeedback(BaseModel):
    word: str
    score: Optional[float] = None
    status: str = ""
    tip: str = ""


class SpeakingAttempt(BaseModel):
    id: str
    child_id: str
    material_id: str
    review_task_id: str = ""
    learning_asset_id: str = ""
    prompt_text: str
    target_text: str = ""
    audio_url: str = ""
    audio_object_key: str = ""
    audio_content_type: str = ""
    audio_size_bytes: int = 0
    audio_duration_ms: int = 0
    transcript: str = ""
    pronunciation_score: Optional[float] = None
    overall_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    fluency_score: Optional[float] = None
    completeness_score: Optional[float] = None
    feedback: str = ""
    word_feedback: list[SpeakingWordFeedback] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    provider: str = ""
    raw_result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str = ""
    status: SpeakingAttemptStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SpeakingAttemptCreate(BaseModel):
    child_id: str
    material_id: str
    prompt_text: str
    transcript: str = ""


class ParentCoachingStep(BaseModel):
    id: str
    title: str
    parent_prompt: str
    stuck_hint: str
    expansion_prompt: str


class ParentCoachingScript(BaseModel):
    id: str
    material_id: str
    title: str
    intro: str
    steps: list[ParentCoachingStep] = Field(default_factory=list)


class LearningAssetMastery(BaseModel):
    asset_id: str
    material_id: str
    material_title: str
    text: str
    kind: str
    translation: str = ""
    image_url: str = ""
    audio_url: str = ""
    mastery_score: float = 0
    mastery_status: str = "needs_practice"
    review_attempts: int = 0
    completed_review_tasks: int = 0
    pending_review_tasks: int = 0
    speaking_attempts: int = 0
    best_speaking_score: Optional[float] = None
    last_speaking_score: Optional[float] = None
    weak_points: list[str] = Field(default_factory=list)
    recommended_action: str = ""


class MaterialReportSummary(BaseModel):
    material_id: str
    title: str
    topic: str = ""
    asset_count: int = 0
    completed_review_tasks: int = 0
    pending_review_tasks: int = 0
    speaking_attempts: int = 0
    average_speaking_score: Optional[float] = None


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
    report_summary: str = ""
    asset_mastery: list[LearningAssetMastery] = Field(default_factory=list)
    material_summaries: list[MaterialReportSummary] = Field(default_factory=list)


class WechatLoginRequest(BaseModel):
    auth_code: str


class PhoneOtpRequest(BaseModel):
    bind_token: str
    phone_number: str


class PhoneOtpResponse(BaseModel):
    request_id: str
    expires_at: datetime
    debug_code: Optional[str] = None


class PhoneBindRequest(BaseModel):
    bind_token: str
    phone_number: str
    otp_code: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class AuthLoginResponse(BaseModel):
    status: AuthStatus
    parent_account: ParentAccount
    children: list[ChildProfile] = Field(default_factory=list)
    tokens: Optional[AuthTokens] = None
    bind_token: Optional[str] = None


class MeResponse(BaseModel):
    parent_account: ParentAccount
    children: list[ChildProfile] = Field(default_factory=list)


class MaterialCreateResponse(BaseModel):
    material: CourseMaterial
    job: MaterialParseJob


class MaterialDetailResponse(BaseModel):
    material: CourseMaterial


class KnowledgePackDetailResponse(BaseModel):
    material: CourseMaterial
    knowledge_pack: KnowledgePack


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTask]


class WeeklyReportResponse(BaseModel):
    report: WeeklyReport


class WeeklyReportResponse(BaseModel):
    report: WeeklyReport


# --------------------------------------------------------------------------- #
# Phonics (自然拼读) — a fixed, authored curriculum decoupled from CourseMaterial.
# --------------------------------------------------------------------------- #


class PhonicsUnitStatus(str, Enum):
    locked = "locked"
    unlocked = "unlocked"
    in_progress = "in_progress"
    mastered = "mastered"


class PhonicsPracticeType(str, Enum):
    none = "none"
    first_sound_tap = "first_sound_tap"
    blend_word_asr = "blend_word_asr"
    heart_word_asr = "heart_word_asr"
    tile_build = "tile_build"
    dictation = "dictation"


class PhonicsAttemptStatus(str, Enum):
    queued = "queued"
    recording_uploaded = "recording_uploaded"
    transcribing = "transcribing"
    scored = "scored"
    no_match = "no_match"
    failed = "failed"


class PhonicsExampleWord(BaseModel):
    text: str
    cn: str = ""


class PhonicsSoundCard(BaseModel):
    id: str
    card_type: str
    letter: str
    phoneme: str = ""
    keyword: str = ""
    keyword_cn: str = ""
    articulation_cue: str = ""
    common_spellings: list[str] = Field(default_factory=list)
    speakable_sound: str = ""
    example_words: list[PhonicsExampleWord] = Field(default_factory=list)
    sound_audio_url: str = ""
    sound_tts_status: MediaGenerationStatus = MediaGenerationStatus.pending
    keyword_audio_url: str = ""
    keyword_tts_status: MediaGenerationStatus = MediaGenerationStatus.pending


class PhonicsWord(BaseModel):
    id: str
    text: str
    segments: list[str] = Field(default_factory=list)
    cn: str = ""
    kind: str = "real"
    audio_url: str = ""
    tts_status: MediaGenerationStatus = MediaGenerationStatus.pending


class PhonicsSentence(BaseModel):
    id: str
    text: str
    cn: str = ""
    audio_url: str = ""
    tts_status: MediaGenerationStatus = MediaGenerationStatus.pending


class PhonicsHeartWord(BaseModel):
    text: str
    cn: str = ""
    audio_url: str = ""
    tts_status: MediaGenerationStatus = MediaGenerationStatus.pending


class PhonicsFirstSoundItem(BaseModel):
    id: str
    word_id: str
    text: str = ""
    cn: str = ""
    answer: str
    options: list[str] = Field(default_factory=list)
    audio_url: str = ""


class PhonicsLessonStep(BaseModel):
    key: str
    practice_type: PhonicsPracticeType = PhonicsPracticeType.none
    title: str = ""
    instruction: str = ""
    card_ids: list[str] = Field(default_factory=list)
    word_ids: list[str] = Field(default_factory=list)
    item_ids: list[str] = Field(default_factory=list)
    heart_words: list[str] = Field(default_factory=list)


class PhonicsUnitProgress(BaseModel):
    unit_id: str
    status: PhonicsUnitStatus = PhonicsUnitStatus.unlocked
    decoding_accuracy: float = 0.0
    first_sound_accuracy: float = 0.0
    grapheme_scores: dict[str, float] = Field(default_factory=dict)
    attempts_count: int = 0
    blended_words: list[str] = Field(default_factory=list)
    mastered: bool = False


class PhonicsUnitSummary(BaseModel):
    id: str
    unit_code: str
    sequence_order: int
    title: str
    subtitle: str = ""
    level: str = "1"
    media_status: MediaGenerationStatus = MediaGenerationStatus.pending
    status: PhonicsUnitStatus = PhonicsUnitStatus.locked
    decoding_accuracy: float = 0.0


class PhonicsCourseInfo(BaseModel):
    id: str
    title: str
    description: str = ""


class PhonicsUnitListResponse(BaseModel):
    course: PhonicsCourseInfo
    units: list[PhonicsUnitSummary] = Field(default_factory=list)
    next_unit_id: str = ""


class PhonicsUnitDetail(BaseModel):
    id: str
    unit_code: str
    sequence_order: int
    title: str
    subtitle: str = ""
    level: str = "1"
    vowel_focus: str = ""
    letters: list[str] = Field(default_factory=list)
    media_status: MediaGenerationStatus = MediaGenerationStatus.pending


class PhonicsUnitDetailResponse(BaseModel):
    unit: PhonicsUnitDetail
    sound_cards: list[PhonicsSoundCard] = Field(default_factory=list)
    decodable_words: list[PhonicsWord] = Field(default_factory=list)
    sentences: list[PhonicsSentence] = Field(default_factory=list)
    heart_words: list[PhonicsHeartWord] = Field(default_factory=list)
    first_sound_items: list[PhonicsFirstSoundItem] = Field(default_factory=list)
    steps: list[PhonicsLessonStep] = Field(default_factory=list)
    progress: PhonicsUnitProgress


class PhonicsAttemptItemResult(BaseModel):
    prompt: str = ""
    expected: str = ""
    given: str = ""
    correct: bool = False


class PhonicsAttempt(BaseModel):
    id: str
    child_id: str
    unit_id: str
    step: str = ""
    practice_type: PhonicsPracticeType
    target_text: str = ""
    item_results: list[PhonicsAttemptItemResult] = Field(default_factory=list)
    accuracy_score: Optional[float] = None
    passed: bool = False
    transcript: str = ""
    feedback: str = ""
    audio_url: str = ""
    provider: str = ""
    failure_reason: str = ""
    status: PhonicsAttemptStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PhonicsTapAttemptCreate(BaseModel):
    child_id: str
    unit_id: str
    step: str = ""
    practice_type: PhonicsPracticeType = PhonicsPracticeType.first_sound_tap
    target_text: str = ""
    item_results: list[PhonicsAttemptItemResult] = Field(default_factory=list)


class PhonicsAttemptResponse(BaseModel):
    attempt: PhonicsAttempt
    progress: PhonicsUnitProgress


class PhonicsProgressResponse(BaseModel):
    course: PhonicsCourseInfo
    units: list[PhonicsUnitProgress] = Field(default_factory=list)
    next_unit_id: str = ""
    mastered_count: int = 0
    total_units: int = 0
