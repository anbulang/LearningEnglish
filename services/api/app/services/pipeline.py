from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol
from uuid import uuid4

from app.models.contracts import (
    CourseMaterial,
    DifficultyBand,
    JobStatus,
    KnowledgePack,
    MaterialParseJob,
    ReviewTask,
    ReviewTaskStatus,
    SentencePattern,
    TaskType,
    VocabularyItem,
)


@dataclass(frozen=True)
class OCRDraft:
    ocr_text: str
    title: str
    topic: str
    vocabulary: list[str]
    sentences: list[str]
    warnings: list[str]
    confidence_summary: str


class OCRProvider(Protocol):
    def extract(self, material: CourseMaterial) -> OCRDraft:
        ...


class LanguageParsingProvider(Protocol):
    def generate_knowledge_pack(
        self,
        material: CourseMaterial,
        job: MaterialParseJob,
    ) -> KnowledgePack:
        ...

    def generate_review_tasks(
        self,
        material: CourseMaterial,
        knowledge_pack: KnowledgePack,
    ) -> list[ReviewTask]:
        ...


class StubOCRProvider:
    def extract(self, material: CourseMaterial) -> OCRDraft:
        topic = material.topic or "课堂主题"
        raw_tokens = [token.strip("?.!,").lower() for token in material.title.split()]
        seed_words = [token for token in raw_tokens if token]
        vocabulary = seed_words[:3] or ["apple", "banana", "cat"]
        sentences = [
            f"What is this in {topic}?",
            f"It is a {vocabulary[0]}.",
        ]
        ocr_text = " ".join(vocabulary + sentences)
        return OCRDraft(
            ocr_text=ocr_text,
            title=material.title,
            topic=topic,
            vocabulary=vocabulary,
            sentences=sentences,
            warnings=["建议家长核对低频词和专有名词。"],
            confidence_summary="OCR 与结构化解析已完成，建议人工快速确认。",
        )


class StubLanguageParsingProvider:
    def generate_knowledge_pack(
        self,
        material: CourseMaterial,
        job: MaterialParseJob,
    ) -> KnowledgePack:
        knowledge_pack_id = f"knowledge_{uuid4().hex[:8]}"
        vocabulary_items = [
            VocabularyItem(
                id=f"word_{uuid4().hex[:8]}",
                knowledge_pack_id=knowledge_pack_id,
                word=word,
                phonics="",
                meaning_cn=f"{word} 的课堂释义",
                image_url="",
                audio_url="",
                example_sentence=job.draft_sentences[0] if job.draft_sentences else "",
            )
            for word in job.draft_vocabulary
        ]
        sentence_patterns = [
            SentencePattern(
                id=f"sentence_{uuid4().hex[:8]}",
                knowledge_pack_id=knowledge_pack_id,
                sentence=sentence,
                meaning_cn="课堂重点句型",
                usage_type="question" if "?" in sentence else "answer",
                audio_url="",
            )
            for sentence in job.draft_sentences
        ]
        return KnowledgePack(
            id=knowledge_pack_id,
            material_id=material.id,
            topic=job.draft_topic or material.topic,
            difficulty_band=DifficultyBand.repeat,
            lesson_summary=f"本课围绕 {job.draft_topic or material.topic} 展开，重点复习 {', '.join(job.draft_vocabulary[:3])}。",
            review_recommendation="先完成词卡和听音选图，再进入家长问答。",
            vocabulary_items=vocabulary_items,
            sentence_patterns=sentence_patterns,
        )

    def generate_review_tasks(
        self,
        material: CourseMaterial,
        knowledge_pack: KnowledgePack,
    ) -> list[ReviewTask]:
        now = datetime.now(timezone.utc)
        words = [item.word for item in knowledge_pack.vocabulary_items[:3]]
        first_word = words[0] if words else "cat"
        return [
            ReviewTask(
                id=f"task_{uuid4().hex[:8]}",
                child_id=material.child_id,
                material_id=material.id,
                task_type=TaskType.flashcard,
                difficulty="recognition",
                content_json={
                    "prompt": "看词卡并跟读",
                    "word": first_word,
                    "assets": {"image": ""},
                    "hints": ["先听标准音，再重复一遍。"],
                },
                due_date=now,
                status=ReviewTaskStatus.pending,
            ),
            ReviewTask(
                id=f"task_{uuid4().hex[:8]}",
                child_id=material.child_id,
                material_id=material.id,
                task_type=TaskType.listen_choice,
                difficulty="repeat",
                content_json={
                    "prompt": "听音选图",
                    "choices": words or ["cat", "dog", "bird"],
                    "correct_answer": first_word,
                    "hints": ["如果不会，可以先点播放两次。"],
                },
                due_date=now,
                status=ReviewTaskStatus.pending,
            ),
            ReviewTask(
                id=f"task_{uuid4().hex[:8]}",
                child_id=material.child_id,
                material_id=material.id,
                task_type=TaskType.match_choice,
                difficulty="comprehension",
                content_json={
                    "prompt": "问句和答句配对",
                    "left": knowledge_pack.sentence_patterns[:1]
                    and [knowledge_pack.sentence_patterns[0].sentence]
                    or ["What is this?"],
                    "right": knowledge_pack.sentence_patterns[1:2]
                    and [knowledge_pack.sentence_patterns[1].sentence]
                    or [f"It is a {first_word}."],
                    "hints": ["家长可以先示范一轮。"],
                },
                due_date=now,
                status=ReviewTaskStatus.pending,
            ),
        ]


class DemoPipelineService:
    def __init__(
        self,
        ocr_provider: Optional[OCRProvider] = None,
        parsing_provider: Optional[LanguageParsingProvider] = None,
    ) -> None:
        self.ocr_provider = ocr_provider or StubOCRProvider()
        self.parsing_provider = parsing_provider or StubLanguageParsingProvider()

    def prepare_job(self, material: CourseMaterial, job: MaterialParseJob) -> MaterialParseJob:
        draft = self.ocr_provider.extract(material)
        return job.model_copy(
            update={
                "status": JobStatus.needs_review,
                "finished_at": datetime.now(timezone.utc),
                "draft_title": draft.title,
                "draft_topic": draft.topic,
                "draft_vocabulary": draft.vocabulary,
                "draft_sentences": draft.sentences,
                "confidence_summary": draft.confidence_summary,
                "warnings": draft.warnings,
            }
        )

    def build_knowledge_assets(
        self,
        material: CourseMaterial,
        job: MaterialParseJob,
    ) -> tuple[KnowledgePack, list[ReviewTask]]:
        knowledge_pack = self.parsing_provider.generate_knowledge_pack(material, job)
        review_tasks = self.parsing_provider.generate_review_tasks(material, knowledge_pack)
        return knowledge_pack, review_tasks
