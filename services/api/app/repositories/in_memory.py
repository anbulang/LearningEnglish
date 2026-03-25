from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from app.models.contracts import (
    ChildProfile,
    CourseMaterial,
    DifficultyBand,
    JobStatus,
    KnowledgePack,
    MaterialParseJob,
    MaterialStatus,
    PracticeSession,
    ReviewTask,
    ReviewTaskStatus,
    SentencePattern,
    TaskType,
    VocabularyItem,
    WeeklyReport,
)


class InMemoryStore:
    def __init__(self) -> None:
        self.children: dict[str, ChildProfile] = {}
        self.materials: dict[str, CourseMaterial] = {}
        self.material_jobs: dict[str, MaterialParseJob] = {}
        self.knowledge_packs: dict[str, KnowledgePack] = {}
        self.review_tasks: dict[str, ReviewTask] = {}
        self.practice_sessions: dict[str, PracticeSession] = {}
        self.weekly_reports: dict[str, WeeklyReport] = {}

    def seed(self) -> None:
        child = ChildProfile(
            id="child_demo_1",
            name="Mia",
            avatar_url="",
            age=6,
            level="Starter",
            learning_goal="会说课堂高频问答和基础单词",
            preferred_review_duration_minutes=10,
            parent_notes="先听再说，效果更好。",
        )
        self.children[child.id] = child
        self.weekly_reports[child.id] = WeeklyReport(
            id=f"report_{uuid4().hex[:8]}",
            child_id=child.id,
            week_start=date(2026, 3, 23),
            week_end=date(2026, 3, 29),
            completed_sessions=0,
            reviewed_words=0,
            speaking_attempts=0,
            weak_items=[],
            recommended_actions=[
                "优先完成今天新课的词卡和听音选图。",
                "家长用 What is this? 做 2 轮问答。",
            ],
        )
        demo_material = CourseMaterial(
            id="material_seed_1",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 3, 24),
            title="Animals Around Me",
            topic="动物",
            status=MaterialStatus.ready,
            source_images=["demo://worksheet-1"],
            pdf_url="demo://worksheet-1.pdf",
            ocr_text="cat dog bird What is this? It is a cat.",
            tags=["动物", "问答"],
        )
        self.materials[demo_material.id] = demo_material
        demo_job = MaterialParseJob(
            id="job_seed_1",
            material_id=demo_material.id,
            status=JobStatus.ready,
            confidence_summary="种子数据已预生成。",
            warnings=[],
            started_at=datetime(2026, 3, 24, 18, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 3, 24, 18, 1, tzinfo=timezone.utc),
            draft_title=demo_material.title,
            draft_topic=demo_material.topic,
            draft_vocabulary=["cat", "dog", "bird"],
            draft_sentences=["What is this?", "It is a cat."],
        )
        self.material_jobs[demo_job.id] = demo_job

        knowledge_pack_id = "knowledge_seed_1"
        knowledge_pack = KnowledgePack(
            id=knowledge_pack_id,
            material_id=demo_material.id,
            topic=demo_material.topic,
            difficulty_band=DifficultyBand.repeat,
            lesson_summary="本课围绕常见动物词和基础问答展开。",
            review_recommendation="先听词卡，再做听音选图。",
            vocabulary_items=[
                VocabularyItem(
                    id="word_seed_cat",
                    knowledge_pack_id=knowledge_pack_id,
                    word="cat",
                    phonics="/kæt/",
                    meaning_cn="猫",
                    image_url="",
                    audio_url="",
                    example_sentence="It is a cat.",
                ),
                VocabularyItem(
                    id="word_seed_dog",
                    knowledge_pack_id=knowledge_pack_id,
                    word="dog",
                    phonics="/dɔːɡ/",
                    meaning_cn="狗",
                    image_url="",
                    audio_url="",
                    example_sentence="This is a dog.",
                ),
                VocabularyItem(
                    id="word_seed_bird",
                    knowledge_pack_id=knowledge_pack_id,
                    word="bird",
                    phonics="/bɜːd/",
                    meaning_cn="鸟",
                    image_url="",
                    audio_url="",
                    example_sentence="I can see a bird.",
                ),
            ],
            sentence_patterns=[
                SentencePattern(
                    id="sentence_seed_1",
                    knowledge_pack_id=knowledge_pack_id,
                    sentence="What is this?",
                    meaning_cn="这是什么？",
                    usage_type="question",
                    audio_url="",
                ),
                SentencePattern(
                    id="sentence_seed_2",
                    knowledge_pack_id=knowledge_pack_id,
                    sentence="It is a cat.",
                    meaning_cn="它是一只猫。",
                    usage_type="answer",
                    audio_url="",
                ),
            ],
        )
        self.knowledge_packs[demo_material.id] = knowledge_pack

        for task_type, difficulty, content in (
            (
                TaskType.flashcard,
                "recognition",
                {"prompt": "看词卡并跟读", "word": "cat"},
            ),
            (
                TaskType.listen_choice,
                "repeat",
                {
                    "prompt": "听音选图",
                    "choices": ["cat", "dog", "bird"],
                    "correct_answer": "cat",
                },
            ),
            (
                TaskType.match_choice,
                "comprehension",
                {
                    "prompt": "问句和答句配对",
                    "left": ["What is this?"],
                    "right": ["It is a cat."],
                },
            ),
        ):
            task = ReviewTask(
                id=f"task_seed_{uuid4().hex[:8]}",
                child_id=child.id,
                material_id=demo_material.id,
                task_type=task_type,
                difficulty=difficulty,
                content_json=content,
                due_date=datetime(2026, 3, 24, 19, 0, tzinfo=timezone.utc),
                status=ReviewTaskStatus.pending,
            )
            self.review_tasks[task.id] = task
