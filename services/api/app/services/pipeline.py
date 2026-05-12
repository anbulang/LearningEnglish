from __future__ import annotations

import json
import base64
import logging
import mimetypes
import os
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
    LearningAsset,
    MaterialImageRecord,
    MaterialParseJob,
    MediaGenerationStatus,
    ParentCoachingScript,
    ParentCoachingStep,
    PrimaryAccent,
    ReviewTask,
    ReviewTaskStatus,
    SentencePattern,
    SourceBoundingBox,
    TaskType,
    VocabularyItem,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCRDraft:
    ocr_text: str
    title: str
    topic: str
    vocabulary: list[str]
    sentences: list[str]
    image_records: list[MaterialImageRecord]
    learning_assets: list[LearningAsset]
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
            image_records=_fallback_image_records(
                material,
                title=material.title,
                ocr_text=ocr_text,
                vocabulary=vocabulary,
                sentences=sentences,
                details=["当前环境未启用真实 OCR，图片级明细使用开发回退结果。"],
            ),
            learning_assets=_fallback_learning_assets(
                material,
                vocabulary=vocabulary,
                sentences=sentences,
            ),
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
        draft_vocabulary = vocabulary[:8] or ["cat", "dog", "bird"]
        draft_sentences = sentences[:6] or ["What is this?", "It is a cat."]
        return OCRDraft(
            ocr_text=ocr_text,
            title=material.title,
            topic=material.topic or _infer_topic(ocr_text),
            vocabulary=draft_vocabulary,
            sentences=draft_sentences,
            image_records=_fallback_image_records(
                material,
                title=material.title,
                ocr_text=ocr_text,
                vocabulary=draft_vocabulary,
                sentences=draft_sentences,
                details=["PaddleOCR 已完成图片级文本抽取，请家长确认。"],
            ),
            learning_assets=_fallback_learning_assets(
                material,
                vocabulary=draft_vocabulary,
                sentences=draft_sentences,
            ),
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
        trust_env: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_or_endpoint = model_or_endpoint
        self.timeout_seconds = timeout_seconds
        self.max_image_count = max_image_count
        self._client = client
        self.trust_env = trust_env

    def extract(self, material: CourseMaterial, local_paths: list[Path]) -> OCRDraft:
        image_paths = local_paths[: self.max_image_count]
        if not image_paths:
            raise DoubaoProviderError("Doubao OCR requires at least one worksheet image")

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "请识别这些低龄儿童英语课堂讲义图片，并只返回 json。"
                    "json 字段必须包含：ocr_text, title, topic, vocabulary, sentences, "
                    "warnings, confidence_summary, image_records, learning_assets。"
                    "vocabulary 只放英文单词或短语，sentences 只放英文句型或课堂对话句子。"
                    "image_records 必须按图片页返回数组，每项包含 page_index, image_title, "
                    "ocr_text, vocabulary, sentences, details。"
                    "learning_assets 常规目标 8 到 15 个，绝对总量 1 到 20 个，每项包含 "
                    "text, kind, translation, source_page_index, source_bbox, "
                    "source_visual_description, pronunciation_text, image_prompt, difficulty, teaching_note。"
                    "source_bbox 使用 0 到 1 的相对坐标；无法定位时可为空。"
                    "不要把教师说明、页码、版权或出版社信息放入 learning_assets。"
                    "如果不确定，请在 warnings 用中文说明。"
                ),
            }
        ]
        for index, path in enumerate(image_paths, start=1):
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"第 {index} 页图片如下。请只把这张图片的 OCR、标题、词汇、句子和细节写入 "
                        f"image_records 中 page_index={index} 的对象；不要混入其他页内容。"
                    ),
                }
            )
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
            trust_env=self.trust_env,
        )
        ocr_text = str(payload.get("ocr_text") or "").strip()
        vocabulary = _clean_string_list(payload.get("vocabulary"))
        sentences = _clean_string_list(payload.get("sentences"))
        draft_vocabulary = vocabulary or _extract_candidate_vocabulary(ocr_text)[:8]
        draft_sentences = sentences or _extract_candidate_sentences([ocr_text])[:6]
        draft_ocr_text = ocr_text or " ".join(draft_vocabulary + draft_sentences)
        image_records = _image_records_from_payload(
            material,
            payload.get("image_records"),
            title=_clean_text_value(payload.get("title")) or material.title,
            ocr_text=draft_ocr_text,
            vocabulary=draft_vocabulary,
            sentences=draft_sentences,
        )
        return OCRDraft(
            ocr_text=draft_ocr_text,
            title=_clean_text_value(payload.get("title")) or material.title,
            topic=_clean_text_value(payload.get("topic")) or material.topic or _infer_topic(ocr_text),
            vocabulary=draft_vocabulary,
            sentences=draft_sentences,
            image_records=image_records,
            learning_assets=_learning_assets_from_payload(
                material,
                payload.get("learning_assets"),
                vocabulary=draft_vocabulary,
                sentences=draft_sentences,
                page_count=max(1, len(image_paths)),
            ),
            warnings=_clean_string_list(payload.get("warnings")),
            confidence_summary=_clean_text_value(payload.get("confidence_summary"))
            or "豆包已完成识别，请家长确认重点词句。",
        )


class DoubaoLanguageParsingProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_or_endpoint: str,
        timeout_seconds: int = 60,
        client: Optional[httpx.Client] = None,
        trust_env: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_or_endpoint = model_or_endpoint
        self.timeout_seconds = timeout_seconds
        self._client = client
        self.trust_env = trust_env

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
            trust_env=self.trust_env,
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
                "draft_image_records": draft.image_records,
                "draft_learning_assets": draft.learning_assets,
                "confidence_summary": draft.confidence_summary,
                "warnings": draft.warnings,
            }
        )

    def build_knowledge_assets(
        self,
        material: CourseMaterial,
        job: MaterialParseJob,
    ) -> tuple[KnowledgePack, list[ReviewTask], ParentCoachingScript]:
        # Confirmation is part of the interactive review flow. The expensive
        # model calls already happened while preparing the draft, so generate
        # final practice assets locally from the reviewed words and sentences.
        local_parser = StubLanguageParsingProvider()
        knowledge_pack = local_parser.generate_knowledge_pack(material, job)
        review_tasks = local_parser.generate_review_tasks(material, knowledge_pack)
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
                trust_env=settings.ai_http_trust_env,
            ),
            parsing_provider=DoubaoLanguageParsingProvider(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                model_or_endpoint=settings.doubao_text_model_or_endpoint,
                timeout_seconds=settings.ai_request_timeout_seconds,
                trust_env=settings.ai_http_trust_env,
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
    trust_env: bool = False,
) -> dict[str, Any]:
    if not api_key:
        raise DoubaoProviderError("Doubao provider requires ARK_API_KEY")
    if not model_or_endpoint:
        raise DoubaoProviderError("Doubao provider requires model or endpoint config")
    owns_client = client is None
    _log_proxy_diagnostics(trust_env=trust_env)
    active_client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
    try:
        response = active_client.post(
            f"{base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_or_endpoint,
                "input": [{"role": "user", "content": _responses_content_from_messages(messages)}],
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

    content = _response_output_text(response)
    if not isinstance(content, str) or not content.strip():
        raise DoubaoProviderError("Doubao response contained empty content")
    try:
        payload = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise DoubaoProviderError("Doubao response content must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise DoubaoProviderError("Doubao response JSON must be an object")
    return payload


def _log_proxy_diagnostics(*, trust_env: bool) -> None:
    proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy")
    present = sorted({key.upper() for key in proxy_keys if os.getenv(key)})
    logger.info("AI HTTP proxy diagnostics: trust_env=%s proxy_env_present=%s", trust_env, present)


def _responses_content_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                output.append({"type": "input_text", "text": text})
            continue
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "text" and item.get("text"):
                text = str(item["text"]).strip()
                if text:
                    output.append({"type": "input_text", "text": text})
            elif item_type == "image_url":
                image_url = item.get("image_url")
                if isinstance(image_url, dict) and image_url.get("url"):
                    output.append({"type": "input_image", "image_url": str(image_url["url"])})
    return output


def _response_output_text(response: httpx.Response) -> str:
    try:
        root = response.json()
    except json.JSONDecodeError as exc:
        raise DoubaoProviderError("Doubao response did not contain valid JSON") from exc

    if isinstance(root.get("output_text"), str):
        return root["output_text"].strip()

    output = root.get("output")
    if not isinstance(output, list):
        raise DoubaoProviderError("Doubao response did not contain output text")

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for entry in content:
            if not isinstance(entry, dict):
                continue
            if isinstance(entry.get("text"), str):
                parts.append(entry["text"])
            elif isinstance(entry.get("output_text"), str):
                parts.append(entry["output_text"])
    return "".join(parts).strip()


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
        text = _clean_text_value(item)
        if text and text not in clean:
            clean.append(text)
    return clean


def _clean_text_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _clean_text_value(item)
            if text and text not in parts:
                parts.append(text)
        return " / ".join(parts)
    if isinstance(value, dict):
        return ""
    return str(value).strip()


def _fallback_image_records(
    material: CourseMaterial,
    *,
    title: str,
    ocr_text: str,
    vocabulary: list[str],
    sentences: list[str],
    details: list[str],
) -> list[MaterialImageRecord]:
    source_records = material.image_records or []
    if not source_records:
        return [
            MaterialImageRecord(
                id=f"image_{uuid4().hex[:12]}",
                page_index=1,
                image_title=title or material.title or "讲义页 1",
                ocr_text=ocr_text,
                vocabulary=vocabulary,
                sentences=sentences,
                details=details,
            )
        ]
    return [
        record.model_copy(
            update={
                "image_title": record.image_title or f"{title or material.title or '讲义'} 第 {record.page_index} 页",
                "ocr_text": record.ocr_text or ocr_text,
                "vocabulary": record.vocabulary or vocabulary,
                "sentences": record.sentences or sentences,
                "details": record.details
                if record.details and record.details != ["图片已上传，等待 AI 识别。"]
                else details,
            }
        )
        for record in source_records
    ]


def _image_records_from_payload(
    material: CourseMaterial,
    raw_records: Any,
    *,
    title: str,
    ocr_text: str,
    vocabulary: list[str],
    sentences: list[str],
) -> list[MaterialImageRecord]:
    fallback = _fallback_image_records(
        material,
        title=title,
        ocr_text=ocr_text,
        vocabulary=vocabulary,
        sentences=sentences,
        details=["AI 已完成图片级识别，请家长确认。"],
    )
    if not isinstance(raw_records, list):
        return fallback

    by_page = {record.page_index: record for record in fallback}
    for index, raw in enumerate(raw_records, start=1):
        if not isinstance(raw, dict):
            continue
        page_index = int(raw.get("page_index") or index)
        base = by_page.get(page_index) or MaterialImageRecord(
            id=f"image_{uuid4().hex[:12]}",
            page_index=page_index,
        )
        by_page[page_index] = base.model_copy(
            update={
                "image_title": _clean_text_value(raw.get("image_title")) or base.image_title,
                "ocr_text": _clean_text_value(raw.get("ocr_text")) or base.ocr_text,
                "vocabulary": _clean_string_list(raw.get("vocabulary")) or base.vocabulary,
                "sentences": _clean_string_list(raw.get("sentences")) or base.sentences,
                "details": _clean_string_list(raw.get("details")) or base.details,
            }
        )
    return [by_page[key] for key in sorted(by_page)]


def _learning_assets_from_payload(
    material: CourseMaterial,
    raw_assets: Any,
    *,
    vocabulary: list[str],
    sentences: list[str],
    page_count: Optional[int] = None,
) -> list[LearningAsset]:
    fallback = _fallback_learning_assets(
        material,
        vocabulary=vocabulary,
        sentences=sentences,
        page_count=page_count,
    )
    if not isinstance(raw_assets, list):
        return fallback

    assets: list[LearningAsset] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_assets, start=1):
        if not isinstance(raw, dict):
            continue
        text = _clean_text_value(raw.get("text"))
        normalized = text.lower()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        assets.append(_learning_asset_from_raw(material, raw, index=index, text=text, page_count=page_count))
        if len(assets) == 20:
            break
    return assets or fallback


def _learning_asset_from_raw(
    material: CourseMaterial,
    raw: dict[str, Any],
    *,
    index: int,
    text: str,
    page_count: Optional[int] = None,
) -> LearningAsset:
    bbox = raw.get("source_bbox")
    source_bbox = None
    if isinstance(bbox, dict):
        source_bbox = _source_bbox_from_raw(bbox)

    kind = _clean_text_value(raw.get("kind")).lower()
    if kind not in {"word", "phrase", "sentence"}:
        kind = "sentence" if " " in text or text.endswith((".", "?", "!")) else "word"

    try:
        page_index = int(raw.get("source_page_index") or 1)
    except (TypeError, ValueError):
        page_index = 1
    effective_page_count = page_count or len(material.image_records) or 1
    page_index = max(1, min(page_index, effective_page_count))

    return LearningAsset(
        id=_clean_text_value(raw.get("id")) or f"asset_{uuid4().hex[:12]}",
        text=text,
        kind=kind,
        translation=_clean_text_value(raw.get("translation")),
        source_page_index=page_index,
        source_bbox=source_bbox,
        source_visual_description=_clean_text_value(raw.get("source_visual_description")),
        pronunciation_text=_clean_text_value(raw.get("pronunciation_text")) or text,
        image_prompt=_clean_text_value(raw.get("image_prompt")) or f"参考讲义内容，为 {text} 生成彩色插图。",
        difficulty=_clean_text_value(raw.get("difficulty")) or "easy",
        teaching_note=_clean_text_value(raw.get("teaching_note")),
        is_core=bool(raw.get("is_core", True)),
        generated_image_status=MediaGenerationStatus.pending,
        tts_us_status=MediaGenerationStatus.pending,
        tts_uk_status=MediaGenerationStatus.pending,
        primary_accent=PrimaryAccent.us,
    )


def _fallback_learning_assets(
    material: CourseMaterial,
    *,
    vocabulary: list[str],
    sentences: list[str],
    page_count: Optional[int] = None,
) -> list[LearningAsset]:
    candidates = [*vocabulary, *sentences]
    assets: list[LearningAsset] = []
    seen: set[str] = set()
    effective_page_count = max(1, page_count or len(material.image_records))
    for index, text in enumerate(candidates, start=1):
        clean = _clean_text_value(text)
        normalized = clean.lower()
        if not clean or normalized in seen:
            continue
        seen.add(normalized)
        kind = (
            "sentence"
            if clean.endswith((".", "?", "!")) or len(clean.split()) > 3
            else "phrase"
            if " " in clean
            else "word"
        )
        assets.append(
            LearningAsset(
                id=f"asset_{uuid4().hex[:12]}",
                text=clean,
                kind=kind,
                translation="",
                source_page_index=((index - 1) % effective_page_count) + 1,
                pronunciation_text=clean,
                image_prompt=f"参考讲义内容，为 {clean} 生成清晰彩色儿童插图。",
                difficulty="easy",
                teaching_note="让孩子先看图，再读英文。",
                is_core=True,
                generated_image_status=MediaGenerationStatus.pending,
                tts_us_status=MediaGenerationStatus.pending,
                tts_uk_status=MediaGenerationStatus.pending,
                primary_accent=PrimaryAccent.us,
            )
        )
        if len(assets) == 20:
            break
    return assets


def _source_bbox_from_raw(raw: dict[str, Any]) -> SourceBoundingBox:
    x = _clamp_float(raw.get("x"), 0.0, 1.0)
    y = _clamp_float(raw.get("y"), 0.0, 1.0)
    width = _clamp_bbox_extent(raw.get("width"), maximum=1.0 - x)
    height = _clamp_bbox_extent(raw.get("height"), maximum=1.0 - y)
    return SourceBoundingBox(x=x, y=y, width=width, height=height)


def _clamp_bbox_extent(value: Any, *, maximum: float) -> float:
    maximum = max(0.0, maximum)
    minimum = min(0.05, maximum)
    return _clamp_float(value, minimum, maximum)


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, parsed))


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
        topic=_clean_text_value(payload.get("topic")) or job.draft_topic or material.topic or "课堂主题",
        difficulty_band=DifficultyBand.repeat,
        lesson_summary=_clean_text_value(payload.get("lesson_summary")) or fallback.lesson_summary,
        review_recommendation=_clean_text_value(payload.get("review_recommendation")) or fallback.review_recommendation,
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
