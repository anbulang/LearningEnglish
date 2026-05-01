from __future__ import annotations

import json
import base64
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol
from uuid import uuid4

import httpx

from app.core.settings import get_settings
from app.models.contracts import (
    CourseMaterial,
    DifficultyBand,
    JobStatus,
    KnowledgePack,
    MaterialParseJob,
    ParentCoachingScript,
    ParentCoachingStep,
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
    def extract(self, material: CourseMaterial, local_paths: list[Path]) -> OCRDraft:
        ...


class LanguageParsingProvider(Protocol):
    def generate_knowledge_pack(self, material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
        ...

    def generate_review_tasks(self, material: CourseMaterial, knowledge_pack: KnowledgePack) -> list[ReviewTask]:
        ...


class DoubaoProviderError(RuntimeError):
    pass


class StubOCRProvider:
    def extract(self, material: CourseMaterial, local_paths: list[Path]) -> OCRDraft:
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
            warnings=["当前环境未启用真实 OCR，已使用可运行的开发回退结果。"],
            confidence_summary="开发环境使用 fallback OCR 草稿，请家长确认后继续。",
        )


class PaddleOCRProvider:
    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("paddleocr is not installed") from exc
        self._ocr = PaddleOCR(use_angle_cls=True, lang="en")

    def extract(self, material: CourseMaterial, local_paths: list[Path]) -> OCRDraft:
        lines: list[str] = []
        confidences: list[float] = []
        for path in local_paths:
            result = self._ocr.ocr(str(path), cls=True)
            for page in result:
                for entry in page or []:
                    if len(entry) < 2:
                        continue
                    text, confidence = entry[1]
                    if text:
                        lines.append(text.strip())
                        confidences.append(float(confidence))
        ocr_text = " ".join(lines)
        vocabulary = _extract_candidate_vocabulary(ocr_text)
        sentences = _extract_candidate_sentences(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        confidence_summary = f"OCR 平均置信度 {avg_confidence:.0%}。"
        warnings = []
        if avg_confidence < 0.78:
            warnings.append("OCR 置信度偏低，建议家长重点检查低频词和整句。")
        return OCRDraft(
            ocr_text=ocr_text,
            title=material.title,
            topic=material.topic or _infer_topic(ocr_text),
            vocabulary=vocabulary[:8] or ["cat", "dog", "bird"],
            sentences=sentences[:6] or ["What is this?", "It is a cat."],
            warnings=warnings,
            confidence_summary=confidence_summary,
        )


class DoubaoVisionOCRProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_or_endpoint: str,
        timeout_seconds: int = 60,
        max_image_count: int = 5,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_or_endpoint = model_or_endpoint
        self.timeout_seconds = timeout_seconds
        self.max_image_count = max_image_count
        self._client = client

    def extract(self, material: CourseMaterial, local_paths: list[Path]) -> OCRDraft:
        image_paths = local_paths[: self.max_image_count]
        if not image_paths:
            raise DoubaoProviderError("Doubao OCR requires at least one worksheet image")

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "请识别这些低龄儿童英语课堂讲义图片，并只返回 json。"
                    "json 字段必须包含：ocr_text, title, topic, vocabulary, sentences, warnings, confidence_summary。"
                    "vocabulary 只放英文单词或短语，sentences 只放英文句型或课堂对话句子。"
                    "如果不确定，请在 warnings 用中文说明。"
                ),
            }
        ]
        for path in image_paths:
            content.append({"type": "image_url", "image_url": {"url": _image_data_url(path)}})

        payload = _post_chat_json(
            api_key=self.api_key,
            base_url=self.base_url,
            model_or_endpoint=self.model_or_endpoint,
            messages=[
                {
                    "role": "system",
                    "content": "你是儿童英语讲义 OCR 和结构化抽取助手。只输出可解析 json，不要输出 Markdown。",
                },
                {"role": "user", "content": content},
            ],
            timeout_seconds=self.timeout_seconds,
            client=self._client,
        )
        ocr_text = str(payload.get("ocr_text") or "").strip()
        vocabulary = _clean_string_list(payload.get("vocabulary"))
        sentences = _clean_string_list(payload.get("sentences"))
        return OCRDraft(
            ocr_text=ocr_text or " ".join(vocabulary + sentences),
            title=str(payload.get("title") or material.title).strip(),
            topic=str(payload.get("topic") or material.topic or _infer_topic(ocr_text)).strip(),
            vocabulary=vocabulary or _extract_candidate_vocabulary(ocr_text)[:8],
            sentences=sentences or _extract_candidate_sentences([ocr_text])[:6],
            warnings=_clean_string_list(payload.get("warnings")),
            confidence_summary=str(payload.get("confidence_summary") or "豆包已完成识别，请家长确认重点词句。").strip(),
        )


class DoubaoLanguageParsingProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_or_endpoint: str,
        timeout_seconds: int = 60,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_or_endpoint = model_or_endpoint
        self.timeout_seconds = timeout_seconds
        self._client = client

    def generate_knowledge_pack(self, material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
        prompt = {
            "material_title": job.draft_title or material.title,
            "topic": job.draft_topic or material.topic,
            "vocabulary": job.draft_vocabulary,
            "sentences": job.draft_sentences,
        }
        payload = _post_chat_json(
            api_key=self.api_key,
            base_url=self.base_url,
            model_or_endpoint=self.model_or_endpoint,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是低龄儿童英语课后复习内容设计助手。只输出 json，字段包含："
                        "topic, lesson_summary, review_recommendation, vocabulary_items, sentence_patterns。"
                        "vocabulary_items 每项包含 word, phonics, meaning_cn, example_sentence。"
                        "sentence_patterns 每项包含 sentence, meaning_cn, usage_type。中文解释要短。"
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            timeout_seconds=self.timeout_seconds,
            client=self._client,
        )
        return _knowledge_pack_from_payload(material, job, payload)

    def generate_review_tasks(self, material: CourseMaterial, knowledge_pack: KnowledgePack) -> list[ReviewTask]:
        return StubLanguageParsingProvider().generate_review_tasks(material, knowledge_pack)


class StubLanguageParsingProvider:
    def generate_knowledge_pack(self, material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
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
            topic=job.draft_topic or material.topic or _infer_topic(job.draft_title),
            difficulty_band=DifficultyBand.repeat,
            lesson_summary=f"本课围绕 {job.draft_topic or material.topic or '课堂主题'} 展开，重点复习 {', '.join(job.draft_vocabulary[:3])}。",
            review_recommendation="先完成词卡和听音选图，再进入家长问答。",
            vocabulary_items=vocabulary_items,
            sentence_patterns=sentence_patterns,
        )

    def generate_review_tasks(self, material: CourseMaterial, knowledge_pack: KnowledgePack) -> list[ReviewTask]:
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


class QwenLanguageParsingProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate_knowledge_pack(self, material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
        prompt = {
            "title": job.draft_title or material.title,
            "topic": job.draft_topic or material.topic,
            "vocabulary": job.draft_vocabulary,
            "sentences": job.draft_sentences,
        }
        response = httpx.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You convert early-childhood English worksheet content into a JSON object "
                            "with keys: topic, lesson_summary, review_recommendation, vocabulary_items, sentence_patterns. "
                            "Keep Chinese explanations short and child-friendly."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        payload = json.loads(content)
        knowledge_pack_id = f"knowledge_{uuid4().hex[:8]}"
        vocabulary_items = [
            VocabularyItem(
                id=f"word_{uuid4().hex[:8]}",
                knowledge_pack_id=knowledge_pack_id,
                word=item["word"],
                phonics=item.get("phonics", ""),
                meaning_cn=item.get("meaning_cn", ""),
                image_url=item.get("image_url", ""),
                audio_url=item.get("audio_url", ""),
                example_sentence=item.get("example_sentence", ""),
            )
            for item in payload.get("vocabulary_items", [])
        ]
        sentence_patterns = [
            SentencePattern(
                id=f"sentence_{uuid4().hex[:8]}",
                knowledge_pack_id=knowledge_pack_id,
                sentence=item["sentence"],
                meaning_cn=item.get("meaning_cn", ""),
                usage_type=item.get("usage_type", ""),
                audio_url=item.get("audio_url", ""),
            )
            for item in payload.get("sentence_patterns", [])
        ]
        return KnowledgePack(
            id=knowledge_pack_id,
            material_id=material.id,
            topic=payload.get("topic") or job.draft_topic or material.topic,
            difficulty_band=DifficultyBand.repeat,
            lesson_summary=payload.get("lesson_summary") or "本课围绕课堂主题展开。",
            review_recommendation=payload.get("review_recommendation") or "先词卡，再做理解练习。",
            vocabulary_items=vocabulary_items or StubLanguageParsingProvider().generate_knowledge_pack(material, job).vocabulary_items,
            sentence_patterns=sentence_patterns or StubLanguageParsingProvider().generate_knowledge_pack(material, job).sentence_patterns,
        )

    def generate_review_tasks(self, material: CourseMaterial, knowledge_pack: KnowledgePack) -> list[ReviewTask]:
        return StubLanguageParsingProvider().generate_review_tasks(material, knowledge_pack)


class ProviderBackedPipelineService:
    def __init__(self, ocr_provider: OCRProvider, parsing_provider: LanguageParsingProvider) -> None:
        self.ocr_provider = ocr_provider
        self.parsing_provider = parsing_provider

    def prepare_job(self, material: CourseMaterial, job: MaterialParseJob, local_paths: list[Path]) -> MaterialParseJob:
        draft = self.ocr_provider.extract(material, local_paths)
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
    ) -> tuple[KnowledgePack, list[ReviewTask], ParentCoachingScript]:
        knowledge_pack = self.parsing_provider.generate_knowledge_pack(material, job)
        review_tasks = self.parsing_provider.generate_review_tasks(material, knowledge_pack)
        coaching_script = ParentCoachingScript(
            id=f"coach_{uuid4().hex[:8]}",
            material_id=material.id,
            title=f"{material.title} 亲子陪练",
            intro="先听、再问、再让孩子完整输出，不需要一次说很长。",
            steps=[
                ParentCoachingStep(
                    id=f"coach_step_{uuid4().hex[:8]}",
                    title="先问孩子看到什么",
                    parent_prompt=f"先问：What is this? 指向 {job.draft_vocabulary[:1] or ['the picture']}。",
                    stuck_hint="如果不会，就先给半句提示：It is a ...",
                    expansion_prompt="孩子说出单词后，再请他完整说一句。",
                ),
                ParentCoachingStep(
                    id=f"coach_step_{uuid4().hex[:8]}",
                    title="引导完整句子",
                    parent_prompt="请孩子完整说：It is a ...",
                    stuck_hint="必要时先由家长完整示范一遍。",
                    expansion_prompt="最后换一个词，让孩子自己替换表达。",
                ),
            ],
        )
        return knowledge_pack, review_tasks, coaching_script


def build_pipeline_service() -> ProviderBackedPipelineService:
    settings = get_settings()
    provider_name = settings.ai_provider.lower().strip()
    if provider_name == "doubao":
        missing = [
            name
            for name, value in {
                "ARK_API_KEY": settings.ark_api_key,
                "DOUBAO_VISION_MODEL_OR_ENDPOINT": settings.doubao_vision_model_or_endpoint,
                "DOUBAO_TEXT_MODEL_OR_ENDPOINT": settings.doubao_text_model_or_endpoint,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Doubao provider is enabled but missing config: {', '.join(missing)}")
        return ProviderBackedPipelineService(
            ocr_provider=DoubaoVisionOCRProvider(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                model_or_endpoint=settings.doubao_vision_model_or_endpoint,
                timeout_seconds=settings.ai_request_timeout_seconds,
                max_image_count=settings.ai_max_image_count,
            ),
            parsing_provider=DoubaoLanguageParsingProvider(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                model_or_endpoint=settings.doubao_text_model_or_endpoint,
                timeout_seconds=settings.ai_request_timeout_seconds,
            ),
        )

    ocr_provider: OCRProvider = StubOCRProvider()
    parsing_provider: LanguageParsingProvider = StubLanguageParsingProvider()
    if provider_name == "qwen" and settings.dashscope_api_key:
        parsing_provider = QwenLanguageParsingProvider(
            api_key=settings.dashscope_api_key,
            model=settings.qwen_model,
        )
    return ProviderBackedPipelineService(ocr_provider=ocr_provider, parsing_provider=parsing_provider)


def _post_chat_json(
    *,
    api_key: str,
    base_url: str,
    model_or_endpoint: str,
    messages: list[dict[str, Any]],
    timeout_seconds: int,
    client: Optional[httpx.Client],
) -> dict[str, Any]:
    if not api_key:
        raise DoubaoProviderError("Doubao provider requires ARK_API_KEY")
    if not model_or_endpoint:
        raise DoubaoProviderError("Doubao provider requires model or endpoint config")
    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout_seconds)
    try:
        response = active_client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_or_endpoint,
                "temperature": 0.2,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise DoubaoProviderError(f"Doubao request timeout after {timeout_seconds}s") from exc
    except httpx.HTTPError as exc:
        raise DoubaoProviderError(f"Doubao request failed: {exc}") from exc
    finally:
        if owns_client:
            active_client.close()

    if response.status_code >= 400:
        detail = _response_error_detail(response)
        raise DoubaoProviderError(f"Doubao API returned HTTP {response.status_code}: {detail}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise DoubaoProviderError("Doubao response did not contain chat message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise DoubaoProviderError("Doubao response contained empty content")
    try:
        payload = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise DoubaoProviderError("Doubao response content must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise DoubaoProviderError("Doubao response JSON must be an object")
    return payload


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text[:300]
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        detail = payload.get("detail") or payload.get("message")
        if detail:
            return str(detail)
    return str(payload)[:300]


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _image_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    clean: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in clean:
            clean.append(text)
    return clean


def _knowledge_pack_from_payload(material: CourseMaterial, job: MaterialParseJob, payload: dict[str, Any]) -> KnowledgePack:
    knowledge_pack_id = f"knowledge_{uuid4().hex[:8]}"
    raw_vocabulary = payload.get("vocabulary_items")
    vocabulary_items = []
    if isinstance(raw_vocabulary, list):
        for item in raw_vocabulary:
            if not isinstance(item, dict) or not item.get("word"):
                continue
            vocabulary_items.append(
                VocabularyItem(
                    id=f"word_{uuid4().hex[:8]}",
                    knowledge_pack_id=knowledge_pack_id,
                    word=str(item["word"]).strip(),
                    phonics=str(item.get("phonics", "")).strip(),
                    meaning_cn=str(item.get("meaning_cn", "")).strip(),
                    image_url=str(item.get("image_url", "")).strip(),
                    audio_url=str(item.get("audio_url", "")).strip(),
                    example_sentence=str(item.get("example_sentence", "")).strip(),
                )
            )
    raw_sentences = payload.get("sentence_patterns")
    sentence_patterns = []
    if isinstance(raw_sentences, list):
        for item in raw_sentences:
            if not isinstance(item, dict) or not item.get("sentence"):
                continue
            sentence_patterns.append(
                SentencePattern(
                    id=f"sentence_{uuid4().hex[:8]}",
                    knowledge_pack_id=knowledge_pack_id,
                    sentence=str(item["sentence"]).strip(),
                    meaning_cn=str(item.get("meaning_cn", "")).strip(),
                    usage_type=str(item.get("usage_type", "")).strip(),
                    audio_url=str(item.get("audio_url", "")).strip(),
                )
            )
    fallback = StubLanguageParsingProvider().generate_knowledge_pack(material, job)
    return KnowledgePack(
        id=knowledge_pack_id,
        material_id=material.id,
        topic=str(payload.get("topic") or job.draft_topic or material.topic or "课堂主题").strip(),
        difficulty_band=DifficultyBand.repeat,
        lesson_summary=str(payload.get("lesson_summary") or fallback.lesson_summary).strip(),
        review_recommendation=str(payload.get("review_recommendation") or fallback.review_recommendation).strip(),
        vocabulary_items=vocabulary_items or fallback.vocabulary_items,
        sentence_patterns=sentence_patterns or fallback.sentence_patterns,
    )


def _extract_candidate_vocabulary(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z]{2,}", text.lower())
    deduped: list[str] = []
    for word in words:
        if word in {"what", "this", "that", "is", "it", "a", "an", "the"}:
            continue
        if word not in deduped:
            deduped.append(word)
    return deduped


def _extract_candidate_sentences(lines: list[str]) -> list[str]:
    sentences: list[str] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        if clean.endswith("?") or clean.endswith(".") or len(clean.split()) > 2:
            sentences.append(clean)
    return sentences


def _infer_topic(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("cat", "dog", "bird", "animal")):
        return "动物"
    if any(word in lowered for word in ("apple", "banana", "fruit")):
        return "水果"
    return "课堂主题"
