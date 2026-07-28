import 'package:meta/meta.dart';

import 'enums.dart';
import 'json.dart';

@immutable
class SourceBoundingBox {
  const SourceBoundingBox({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  final double height;
  final double width;
  final double x;
  final double y;

  factory SourceBoundingBox.fromJson(JsonMap json) {
    return SourceBoundingBox(
      x: doubleFromJson(json['x']) ?? 0,
      y: doubleFromJson(json['y']) ?? 0,
      width: doubleFromJson(json['width']) ?? 1,
      height: doubleFromJson(json['height']) ?? 1,
    );
  }

  JsonMap toJson() => {
        'x': x,
        'y': y,
        'width': width,
        'height': height,
      };
}

@immutable
class LearningAsset {
  const LearningAsset({
    required this.id,
    required this.text,
    required this.kind,
    this.translation = '',
    this.sourcePageIndex = 1,
    this.sourceBbox,
    this.sourceVisualDescription = '',
    this.pronunciationText = '',
    this.imagePrompt = '',
    this.difficulty = 'easy',
    this.teachingNote = '',
    this.isCore = true,
    this.generatedImageStatus = 'pending',
    this.generatedImageUrl = '',
    this.generatedImageObjectKey = '',
    this.generatedImageError = '',
    this.ttsUsStatus = 'pending',
    this.ttsUsUrl = '',
    this.ttsUsObjectKey = '',
    this.ttsUsError = '',
    this.ttsUkStatus = 'pending',
    this.ttsUkUrl = '',
    this.ttsUkObjectKey = '',
    this.ttsUkError = '',
    this.primaryAccent = 'us',
  });

  final String difficulty;
  final String generatedImageObjectKey;
  final String generatedImageError;
  final String generatedImageStatus;
  final String generatedImageUrl;
  final String id;
  final String imagePrompt;
  final bool isCore;
  final String kind;
  final String primaryAccent;
  final String pronunciationText;
  final SourceBoundingBox? sourceBbox;
  final int sourcePageIndex;
  final String sourceVisualDescription;
  final String teachingNote;
  final String text;
  final String translation;
  final String ttsUkObjectKey;
  final String ttsUkError;
  final String ttsUkStatus;
  final String ttsUkUrl;
  final String ttsUsObjectKey;
  final String ttsUsError;
  final String ttsUsStatus;
  final String ttsUsUrl;

  factory LearningAsset.fromJson(JsonMap json) {
    final sourceBbox = json['source_bbox'];
    return LearningAsset(
      id: json['id'] as String? ?? '',
      text: json['text'] as String? ?? '',
      kind: json['kind'] as String? ?? 'word',
      translation: json['translation'] as String? ?? '',
      sourcePageIndex: json['source_page_index'] as int? ?? 1,
      sourceBbox:
          sourceBbox is JsonMap ? SourceBoundingBox.fromJson(sourceBbox) : null,
      sourceVisualDescription:
          json['source_visual_description'] as String? ?? '',
      pronunciationText: json['pronunciation_text'] as String? ?? '',
      imagePrompt: json['image_prompt'] as String? ?? '',
      difficulty: json['difficulty'] as String? ?? 'easy',
      teachingNote: json['teaching_note'] as String? ?? '',
      isCore: json['is_core'] as bool? ?? true,
      generatedImageStatus:
          json['generated_image_status'] as String? ?? 'pending',
      generatedImageUrl: json['generated_image_url'] as String? ?? '',
      generatedImageObjectKey:
          json['generated_image_object_key'] as String? ?? '',
      generatedImageError: json['generated_image_error'] as String? ?? '',
      ttsUsStatus: json['tts_us_status'] as String? ?? 'pending',
      ttsUsUrl: json['tts_us_url'] as String? ?? '',
      ttsUsObjectKey: json['tts_us_object_key'] as String? ?? '',
      ttsUsError: json['tts_us_error'] as String? ?? '',
      ttsUkStatus: json['tts_uk_status'] as String? ?? 'pending',
      ttsUkUrl: json['tts_uk_url'] as String? ?? '',
      ttsUkObjectKey: json['tts_uk_object_key'] as String? ?? '',
      ttsUkError: json['tts_uk_error'] as String? ?? '',
      primaryAccent: json['primary_accent'] as String? ?? 'us',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'text': text,
        'kind': kind,
        'translation': translation,
        'source_page_index': sourcePageIndex,
        'source_bbox': sourceBbox?.toJson(),
        'source_visual_description': sourceVisualDescription,
        'pronunciation_text': pronunciationText,
        'image_prompt': imagePrompt,
        'difficulty': difficulty,
        'teaching_note': teachingNote,
        'is_core': isCore,
        'generated_image_status': generatedImageStatus,
        'generated_image_url': generatedImageUrl,
        'generated_image_object_key': generatedImageObjectKey,
        'generated_image_error': generatedImageError,
        'tts_us_status': ttsUsStatus,
        'tts_us_url': ttsUsUrl,
        'tts_us_object_key': ttsUsObjectKey,
        'tts_us_error': ttsUsError,
        'tts_uk_status': ttsUkStatus,
        'tts_uk_url': ttsUkUrl,
        'tts_uk_object_key': ttsUkObjectKey,
        'tts_uk_error': ttsUkError,
        'primary_accent': primaryAccent,
      };
}

List<LearningAsset> learningAssetsFromJson(dynamic value) {
  if (value is! List) {
    return const <LearningAsset>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map((item) => LearningAsset.fromJson(item))
      .toList();
}

@immutable
class ChildProfile {
  const ChildProfile({
    required this.id,
    required this.name,
    required this.avatarUrl,
    required this.age,
    required this.level,
    required this.learningGoal,
    required this.preferredReviewDurationMinutes,
    required this.parentNotes,
    this.accent = 'us',
  });

  final String id;
  final String avatarUrl;
  final int age;
  final String learningGoal;
  final String level;
  final String name;
  final String parentNotes;
  final int preferredReviewDurationMinutes;

  /// Preferred TTS accent for this child: `'us'` (American) or `'uk'` (British).
  final String accent;

  factory ChildProfile.fromJson(JsonMap json) {
    return ChildProfile(
      id: json['id'] as String,
      name: json['name'] as String,
      avatarUrl: (json['avatar_url'] ?? '') as String,
      age: json['age'] as int,
      level: json['level'] as String,
      learningGoal: json['learning_goal'] as String,
      preferredReviewDurationMinutes:
          json['preferred_review_duration_minutes'] as int,
      parentNotes: (json['parent_notes'] ?? '') as String,
      accent: json['accent'] as String? ?? 'us',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'name': name,
        'avatar_url': avatarUrl,
        'age': age,
        'level': level,
        'learning_goal': learningGoal,
        'preferred_review_duration_minutes': preferredReviewDurationMinutes,
        'parent_notes': parentNotes,
        'accent': accent,
      };

  ChildProfile copyWith({
    String? id,
    String? name,
    String? avatarUrl,
    int? age,
    String? level,
    String? learningGoal,
    int? preferredReviewDurationMinutes,
    String? parentNotes,
    String? accent,
  }) {
    return ChildProfile(
      id: id ?? this.id,
      name: name ?? this.name,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      age: age ?? this.age,
      level: level ?? this.level,
      learningGoal: learningGoal ?? this.learningGoal,
      preferredReviewDurationMinutes:
          preferredReviewDurationMinutes ?? this.preferredReviewDurationMinutes,
      parentNotes: parentNotes ?? this.parentNotes,
      accent: accent ?? this.accent,
    );
  }
}

@immutable
class CourseMaterial {
  const CourseMaterial({
    required this.id,
    required this.childId,
    required this.parseJobId,
    required this.teacherName,
    required this.lessonDate,
    required this.title,
    required this.topic,
    required this.status,
    required this.sourceImages,
    required this.pdfUrl,
    required this.ocrText,
    required this.tags,
    this.imageRecords = const <MaterialImageRecord>[],
    this.learningAssets = const <LearningAsset>[],
  });

  final String childId;
  final String id;
  final List<MaterialImageRecord> imageRecords;
  final List<LearningAsset> learningAssets;
  final DateTime lessonDate;
  final String ocrText;
  final String parseJobId;
  final String pdfUrl;
  final List<String> sourceImages;
  final MaterialStatus status;
  final List<String> tags;
  final String teacherName;
  final String title;
  final String topic;

  factory CourseMaterial.fromJson(JsonMap json) {
    return CourseMaterial(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      parseJobId: json['parse_job_id'] as String? ?? '',
      teacherName: json['teacher_name'] as String? ?? '',
      lessonDate: dateTimeFromJson(json['lesson_date']) ?? DateTime.now(),
      title: json['title'] as String,
      topic: json['topic'] as String? ?? '',
      status: MaterialStatus.fromJson(json['status'] as String),
      sourceImages: stringListFromJson(json['source_images']),
      pdfUrl: json['pdf_url'] as String? ?? '',
      ocrText: json['ocr_text'] as String? ?? '',
      tags: stringListFromJson(json['tags']),
      imageRecords: materialImageRecordsFromJson(json['image_records']),
      learningAssets: learningAssetsFromJson(json['learning_assets']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'parse_job_id': parseJobId,
        'teacher_name': teacherName,
        'lesson_date': lessonDate.toIso8601String(),
        'title': title,
        'topic': topic,
        'status': status.value,
        'source_images': sourceImages,
        'pdf_url': pdfUrl,
        'ocr_text': ocrText,
        'tags': tags,
        'image_records': imageRecords.map((item) => item.toJson()).toList(),
        'learning_assets': learningAssets.map((item) => item.toJson()).toList(),
      };
}

@immutable
class MaterialImageRecord {
  const MaterialImageRecord({
    required this.id,
    required this.pageIndex,
    required this.sourceType,
    required this.originalFilename,
    required this.url,
    required this.objectKey,
    required this.contentType,
    required this.sizeBytes,
    required this.imageTitle,
    required this.ocrText,
    required this.vocabulary,
    required this.sentences,
    required this.details,
  });

  final String contentType;
  final List<String> details;
  final String id;
  final String imageTitle;
  final String objectKey;
  final String ocrText;
  final String originalFilename;
  final int pageIndex;
  final List<String> sentences;
  final int sizeBytes;
  final String sourceType;
  final String url;
  final List<String> vocabulary;

  factory MaterialImageRecord.fromJson(JsonMap json) {
    return MaterialImageRecord(
      id: json['id'] as String? ?? '',
      pageIndex: json['page_index'] as int? ?? 0,
      sourceType: json['source_type'] as String? ?? 'gallery',
      originalFilename: json['original_filename'] as String? ?? '',
      url: json['url'] as String? ?? '',
      objectKey: json['object_key'] as String? ?? '',
      contentType: json['content_type'] as String? ?? '',
      sizeBytes: json['size_bytes'] as int? ?? 0,
      imageTitle: json['image_title'] as String? ?? '',
      ocrText: json['ocr_text'] as String? ?? '',
      vocabulary: stringListFromJson(json['vocabulary']),
      sentences: stringListFromJson(json['sentences']),
      details: stringListFromJson(json['details']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'page_index': pageIndex,
        'source_type': sourceType,
        'original_filename': originalFilename,
        'url': url,
        'object_key': objectKey,
        'content_type': contentType,
        'size_bytes': sizeBytes,
        'image_title': imageTitle,
        'ocr_text': ocrText,
        'vocabulary': vocabulary,
        'sentences': sentences,
        'details': details,
      };
}

List<MaterialImageRecord> materialImageRecordsFromJson(dynamic value) {
  if (value is! List) {
    return const <MaterialImageRecord>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map((item) => MaterialImageRecord.fromJson(item))
      .toList();
}

@immutable
class MaterialParseJob {
  const MaterialParseJob({
    required this.id,
    required this.materialId,
    required this.status,
    required this.confidenceSummary,
    required this.warnings,
    required this.startedAt,
    required this.finishedAt,
    required this.draftTitle,
    required this.draftTopic,
    required this.draftVocabulary,
    required this.draftSentences,
    this.draftImageRecords = const <MaterialImageRecord>[],
    this.draftLearningAssets = const <LearningAsset>[],
  });

  final String confidenceSummary;
  final List<MaterialImageRecord> draftImageRecords;
  final List<LearningAsset> draftLearningAssets;
  final List<String> draftSentences;
  final String draftTitle;
  final String draftTopic;
  final List<String> draftVocabulary;
  final DateTime? finishedAt;
  final String id;
  final String materialId;
  final DateTime startedAt;
  final JobStatus status;
  final List<String> warnings;

  factory MaterialParseJob.fromJson(JsonMap json) {
    return MaterialParseJob(
      id: json['id'] as String,
      materialId: json['material_id'] as String,
      status: JobStatus.fromJson(json['status'] as String),
      confidenceSummary: json['confidence_summary'] as String? ?? '',
      warnings: stringListFromJson(json['warnings']),
      startedAt: dateTimeFromJson(json['started_at']) ?? DateTime.now(),
      finishedAt: dateTimeFromJson(json['finished_at']),
      draftTitle: json['draft_title'] as String? ?? '',
      draftTopic: json['draft_topic'] as String? ?? '',
      draftVocabulary: stringListFromJson(json['draft_vocabulary']),
      draftSentences: stringListFromJson(json['draft_sentences']),
      draftImageRecords:
          materialImageRecordsFromJson(json['draft_image_records']),
      draftLearningAssets:
          learningAssetsFromJson(json['draft_learning_assets']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'material_id': materialId,
        'status': status.value,
        'confidence_summary': confidenceSummary,
        'warnings': warnings,
        'started_at': startedAt.toIso8601String(),
        'finished_at': finishedAt?.toIso8601String(),
        'draft_title': draftTitle,
        'draft_topic': draftTopic,
        'draft_vocabulary': draftVocabulary,
        'draft_sentences': draftSentences,
        'draft_image_records':
            draftImageRecords.map((item) => item.toJson()).toList(),
        'draft_learning_assets':
            draftLearningAssets.map((item) => item.toJson()).toList(),
      };
}

@immutable
class VocabularyItem {
  const VocabularyItem({
    required this.id,
    required this.knowledgePackId,
    required this.word,
    required this.phonics,
    required this.meaningCn,
    required this.imageUrl,
    required this.audioUrl,
    required this.exampleSentence,
  });

  final String audioUrl;
  final String exampleSentence;
  final String id;
  final String imageUrl;
  final String knowledgePackId;
  final String meaningCn;
  final String phonics;
  final String word;

  factory VocabularyItem.fromJson(JsonMap json) {
    return VocabularyItem(
      id: json['id'] as String,
      knowledgePackId: json['knowledge_pack_id'] as String,
      word: json['word'] as String,
      phonics: json['phonics'] as String? ?? '',
      meaningCn: json['meaning_cn'] as String? ?? '',
      imageUrl: json['image_url'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      exampleSentence: json['example_sentence'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'knowledge_pack_id': knowledgePackId,
        'word': word,
        'phonics': phonics,
        'meaning_cn': meaningCn,
        'image_url': imageUrl,
        'audio_url': audioUrl,
        'example_sentence': exampleSentence,
      };
}

@immutable
class SentencePattern {
  const SentencePattern({
    required this.id,
    required this.knowledgePackId,
    required this.sentence,
    required this.meaningCn,
    required this.usageType,
    required this.audioUrl,
  });

  final String audioUrl;
  final String id;
  final String knowledgePackId;
  final String meaningCn;
  final String sentence;
  final String usageType;

  factory SentencePattern.fromJson(JsonMap json) {
    return SentencePattern(
      id: json['id'] as String,
      knowledgePackId: json['knowledge_pack_id'] as String,
      sentence: json['sentence'] as String,
      meaningCn: json['meaning_cn'] as String? ?? '',
      usageType: json['usage_type'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'knowledge_pack_id': knowledgePackId,
        'sentence': sentence,
        'meaning_cn': meaningCn,
        'usage_type': usageType,
        'audio_url': audioUrl,
      };
}

@immutable
class KnowledgePack {
  const KnowledgePack({
    required this.id,
    required this.materialId,
    required this.topic,
    required this.difficultyBand,
    required this.lessonSummary,
    required this.reviewRecommendation,
    required this.vocabularyItems,
    required this.sentencePatterns,
  });

  final DifficultyBand difficultyBand;
  final String id;
  final String lessonSummary;
  final String materialId;
  final String reviewRecommendation;
  final List<SentencePattern> sentencePatterns;
  final String topic;
  final List<VocabularyItem> vocabularyItems;

  factory KnowledgePack.fromJson(JsonMap json) {
    return KnowledgePack(
      id: json['id'] as String,
      materialId: json['material_id'] as String,
      topic: json['topic'] as String? ?? '',
      difficultyBand:
          DifficultyBand.fromJson(json['difficulty_band'] as String),
      lessonSummary: json['lesson_summary'] as String? ?? '',
      reviewRecommendation: json['review_recommendation'] as String? ?? '',
      vocabularyItems: (json['vocabulary_items'] as List<dynamic>? ?? const [])
          .map((item) => VocabularyItem.fromJson(item as JsonMap))
          .toList(),
      sentencePatterns:
          (json['sentence_patterns'] as List<dynamic>? ?? const [])
              .map((item) => SentencePattern.fromJson(item as JsonMap))
              .toList(),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'material_id': materialId,
        'topic': topic,
        'difficulty_band': difficultyBand.value,
        'lesson_summary': lessonSummary,
        'review_recommendation': reviewRecommendation,
        'vocabulary_items':
            vocabularyItems.map((item) => item.toJson()).toList(),
        'sentence_patterns':
            sentencePatterns.map((item) => item.toJson()).toList(),
      };
}

@immutable
class ReviewTask {
  const ReviewTask({
    required this.id,
    required this.childId,
    required this.materialId,
    required this.taskType,
    required this.difficulty,
    required this.contentJson,
    required this.dueDate,
    required this.status,
  });

  final String childId;
  final JsonMap contentJson;
  final String difficulty;
  final DateTime dueDate;
  final String id;
  final String materialId;
  final ReviewTaskStatus status;
  final TaskType taskType;

  factory ReviewTask.fromJson(JsonMap json) {
    return ReviewTask(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      materialId: json['material_id'] as String,
      taskType: TaskType.fromJson(json['task_type'] as String),
      difficulty: json['difficulty'] as String,
      contentJson: (json['content_json'] as JsonMap?) ?? <String, dynamic>{},
      dueDate: dateTimeFromJson(json['due_date']) ?? DateTime.now(),
      status: ReviewTaskStatus.fromJson(json['status'] as String),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'material_id': materialId,
        'task_type': taskType.value,
        'difficulty': difficulty,
        'content_json': contentJson,
        'due_date': dueDate.toIso8601String(),
        'status': status.value,
      };
}

@immutable
class PracticeSession {
  const PracticeSession({
    required this.id,
    required this.childId,
    required this.reviewTaskIds,
    required this.startedAt,
    required this.completedAt,
    required this.score,
    required this.weakPoints,
  });

  final String childId;
  final DateTime? completedAt;
  final String id;
  final List<String> reviewTaskIds;
  final double score;
  final DateTime startedAt;
  final List<String> weakPoints;

  factory PracticeSession.fromJson(JsonMap json) {
    return PracticeSession(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      reviewTaskIds: stringListFromJson(json['review_task_ids']),
      startedAt: dateTimeFromJson(json['started_at']) ?? DateTime.now(),
      completedAt: dateTimeFromJson(json['completed_at']),
      score: doubleFromJson(json['score']) ?? 0,
      weakPoints: stringListFromJson(json['weak_points']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'review_task_ids': reviewTaskIds,
        'started_at': startedAt.toIso8601String(),
        'completed_at': completedAt?.toIso8601String(),
        'score': score,
        'weak_points': weakPoints,
      };
}

@immutable
class SpeakingWordFeedback {
  const SpeakingWordFeedback({
    required this.word,
    this.score,
    this.status = '',
    this.tip = '',
  });

  final double? score;
  final String status;
  final String tip;
  final String word;

  factory SpeakingWordFeedback.fromJson(JsonMap json) {
    return SpeakingWordFeedback(
      word: json['word'] as String? ?? '',
      score: doubleFromJson(json['score']),
      status: json['status'] as String? ?? '',
      tip: json['tip'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'word': word,
        'score': score,
        'status': status,
        'tip': tip,
      };
}

List<SpeakingWordFeedback> speakingWordFeedbackFromJson(dynamic value) {
  if (value is! List) {
    return const <SpeakingWordFeedback>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map((item) => SpeakingWordFeedback.fromJson(item))
      .toList();
}

@immutable
class SpeakingAttempt {
  const SpeakingAttempt({
    required this.id,
    required this.childId,
    required this.materialId,
    required this.promptText,
    required this.audioUrl,
    required this.transcript,
    required this.pronunciationScore,
    required this.feedback,
    required this.status,
    this.reviewTaskId = '',
    this.learningAssetId = '',
    this.targetText = '',
    this.audioObjectKey = '',
    this.audioContentType = '',
    this.audioSizeBytes = 0,
    this.audioDurationMs = 0,
    this.overallScore,
    this.accuracyScore,
    this.fluencyScore,
    this.completenessScore,
    this.wordFeedback = const <SpeakingWordFeedback>[],
    this.suggestions = const <String>[],
    this.provider = '',
    this.rawResult = const <String, dynamic>{},
    this.failureReason = '',
    this.createdAt,
    this.updatedAt,
  });

  final double? accuracyScore;
  final String audioContentType;
  final int audioDurationMs;
  final String audioObjectKey;
  final int audioSizeBytes;
  final String audioUrl;
  final String childId;
  final double? completenessScore;
  final DateTime? createdAt;
  final String failureReason;
  final String feedback;
  final double? fluencyScore;
  final String id;
  final String learningAssetId;
  final String materialId;
  final double? overallScore;
  final String promptText;
  final double? pronunciationScore;
  final String provider;
  final JsonMap rawResult;
  final String reviewTaskId;
  final SpeakingAttemptStatus status;
  final List<String> suggestions;
  final String targetText;
  final String transcript;
  final DateTime? updatedAt;
  final List<SpeakingWordFeedback> wordFeedback;

  factory SpeakingAttempt.fromJson(JsonMap json) {
    return SpeakingAttempt(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      materialId: json['material_id'] as String,
      reviewTaskId: json['review_task_id'] as String? ?? '',
      learningAssetId: json['learning_asset_id'] as String? ?? '',
      promptText: json['prompt_text'] as String,
      targetText: json['target_text'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      audioObjectKey: json['audio_object_key'] as String? ?? '',
      audioContentType: json['audio_content_type'] as String? ?? '',
      audioSizeBytes: json['audio_size_bytes'] as int? ?? 0,
      audioDurationMs: json['audio_duration_ms'] as int? ?? 0,
      transcript: json['transcript'] as String? ?? '',
      pronunciationScore: doubleFromJson(json['pronunciation_score']),
      overallScore: doubleFromJson(json['overall_score']),
      accuracyScore: doubleFromJson(json['accuracy_score']),
      fluencyScore: doubleFromJson(json['fluency_score']),
      completenessScore: doubleFromJson(json['completeness_score']),
      feedback: json['feedback'] as String? ?? '',
      wordFeedback: speakingWordFeedbackFromJson(json['word_feedback']),
      suggestions: stringListFromJson(json['suggestions']),
      provider: json['provider'] as String? ?? '',
      rawResult: (json['raw_result'] as JsonMap?) ?? const <String, dynamic>{},
      failureReason: json['failure_reason'] as String? ?? '',
      status: SpeakingAttemptStatus.fromJson(json['status'] as String),
      createdAt: dateTimeFromJson(json['created_at']),
      updatedAt: dateTimeFromJson(json['updated_at']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'material_id': materialId,
        'review_task_id': reviewTaskId,
        'learning_asset_id': learningAssetId,
        'prompt_text': promptText,
        'target_text': targetText,
        'audio_url': audioUrl,
        'audio_object_key': audioObjectKey,
        'audio_content_type': audioContentType,
        'audio_size_bytes': audioSizeBytes,
        'audio_duration_ms': audioDurationMs,
        'transcript': transcript,
        'pronunciation_score': pronunciationScore,
        'overall_score': overallScore,
        'accuracy_score': accuracyScore,
        'fluency_score': fluencyScore,
        'completeness_score': completenessScore,
        'feedback': feedback,
        'word_feedback': wordFeedback.map((item) => item.toJson()).toList(),
        'suggestions': suggestions,
        'provider': provider,
        'raw_result': rawResult,
        'failure_reason': failureReason,
        'status': status.value,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };
}

@immutable
class ParentCoachingStep {
  const ParentCoachingStep({
    required this.id,
    required this.title,
    required this.parentPrompt,
    required this.stuckHint,
    required this.expansionPrompt,
  });

  final String expansionPrompt;
  final String id;
  final String parentPrompt;
  final String stuckHint;
  final String title;

  factory ParentCoachingStep.fromJson(JsonMap json) {
    return ParentCoachingStep(
      id: json['id'] as String,
      title: json['title'] as String,
      parentPrompt: json['parent_prompt'] as String,
      stuckHint: json['stuck_hint'] as String,
      expansionPrompt: json['expansion_prompt'] as String,
    );
  }

  JsonMap toJson() => {
        'id': id,
        'title': title,
        'parent_prompt': parentPrompt,
        'stuck_hint': stuckHint,
        'expansion_prompt': expansionPrompt,
      };
}

@immutable
class ParentCoachingScript {
  const ParentCoachingScript({
    required this.id,
    required this.materialId,
    required this.title,
    required this.intro,
    required this.steps,
  });

  final String id;
  final String intro;
  final String materialId;
  final List<ParentCoachingStep> steps;
  final String title;

  factory ParentCoachingScript.fromJson(JsonMap json) {
    return ParentCoachingScript(
      id: json['id'] as String,
      materialId: json['material_id'] as String,
      title: json['title'] as String,
      intro: json['intro'] as String,
      steps: (json['steps'] as List<dynamic>? ?? const [])
          .map((item) => ParentCoachingStep.fromJson(item as JsonMap))
          .toList(),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'material_id': materialId,
        'title': title,
        'intro': intro,
        'steps': steps.map((step) => step.toJson()).toList(),
      };
}

@immutable
class LearningAssetMastery {
  const LearningAssetMastery({
    required this.assetId,
    required this.materialId,
    required this.materialTitle,
    required this.text,
    required this.kind,
    required this.masteryScore,
    required this.masteryStatus,
    required this.reviewAttempts,
    required this.completedReviewTasks,
    required this.pendingReviewTasks,
    required this.speakingAttempts,
    required this.weakPoints,
    required this.recommendedAction,
    this.translation = '',
    this.imageUrl = '',
    this.audioUrl = '',
    this.bestSpeakingScore,
    this.lastSpeakingScore,
  });

  final String assetId;
  final String audioUrl;
  final double? bestSpeakingScore;
  final int completedReviewTasks;
  final String imageUrl;
  final String kind;
  final double? lastSpeakingScore;
  final String masteryStatus;
  final double masteryScore;
  final String materialId;
  final String materialTitle;
  final int pendingReviewTasks;
  final String recommendedAction;
  final int reviewAttempts;
  final int speakingAttempts;
  final String text;
  final String translation;
  final List<String> weakPoints;

  factory LearningAssetMastery.fromJson(JsonMap json) {
    return LearningAssetMastery(
      assetId: json['asset_id'] as String? ?? '',
      materialId: json['material_id'] as String? ?? '',
      materialTitle: json['material_title'] as String? ?? '',
      text: json['text'] as String? ?? '',
      kind: json['kind'] as String? ?? 'word',
      translation: json['translation'] as String? ?? '',
      imageUrl: json['image_url'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      masteryScore: doubleFromJson(json['mastery_score']) ?? 0,
      masteryStatus: json['mastery_status'] as String? ?? 'needs_practice',
      reviewAttempts: json['review_attempts'] as int? ?? 0,
      completedReviewTasks: json['completed_review_tasks'] as int? ?? 0,
      pendingReviewTasks: json['pending_review_tasks'] as int? ?? 0,
      speakingAttempts: json['speaking_attempts'] as int? ?? 0,
      bestSpeakingScore: doubleFromJson(json['best_speaking_score']),
      lastSpeakingScore: doubleFromJson(json['last_speaking_score']),
      weakPoints: stringListFromJson(json['weak_points']),
      recommendedAction: json['recommended_action'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'asset_id': assetId,
        'material_id': materialId,
        'material_title': materialTitle,
        'text': text,
        'kind': kind,
        'translation': translation,
        'image_url': imageUrl,
        'audio_url': audioUrl,
        'mastery_score': masteryScore,
        'mastery_status': masteryStatus,
        'review_attempts': reviewAttempts,
        'completed_review_tasks': completedReviewTasks,
        'pending_review_tasks': pendingReviewTasks,
        'speaking_attempts': speakingAttempts,
        'best_speaking_score': bestSpeakingScore,
        'last_speaking_score': lastSpeakingScore,
        'weak_points': weakPoints,
        'recommended_action': recommendedAction,
      };
}

List<LearningAssetMastery> learningAssetMasteryFromJson(dynamic value) {
  if (value is! List) {
    return const <LearningAssetMastery>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map((item) => LearningAssetMastery.fromJson(item))
      .toList();
}

@immutable
class MaterialReportSummary {
  const MaterialReportSummary({
    required this.materialId,
    required this.title,
    required this.assetCount,
    required this.completedReviewTasks,
    required this.pendingReviewTasks,
    required this.speakingAttempts,
    this.topic = '',
    this.averageSpeakingScore,
  });

  final double? averageSpeakingScore;
  final int assetCount;
  final int completedReviewTasks;
  final String materialId;
  final int pendingReviewTasks;
  final int speakingAttempts;
  final String title;
  final String topic;

  factory MaterialReportSummary.fromJson(JsonMap json) {
    return MaterialReportSummary(
      materialId: json['material_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      assetCount: json['asset_count'] as int? ?? 0,
      completedReviewTasks: json['completed_review_tasks'] as int? ?? 0,
      pendingReviewTasks: json['pending_review_tasks'] as int? ?? 0,
      speakingAttempts: json['speaking_attempts'] as int? ?? 0,
      averageSpeakingScore: doubleFromJson(json['average_speaking_score']),
    );
  }

  JsonMap toJson() => {
        'material_id': materialId,
        'title': title,
        'topic': topic,
        'asset_count': assetCount,
        'completed_review_tasks': completedReviewTasks,
        'pending_review_tasks': pendingReviewTasks,
        'speaking_attempts': speakingAttempts,
        'average_speaking_score': averageSpeakingScore,
      };
}

List<MaterialReportSummary> materialReportSummariesFromJson(dynamic value) {
  if (value is! List) {
    return const <MaterialReportSummary>[];
  }
  return value
      .whereType<Map<String, dynamic>>()
      .map((item) => MaterialReportSummary.fromJson(item))
      .toList();
}

@immutable
class WeeklyReport {
  const WeeklyReport({
    required this.id,
    required this.childId,
    required this.weekStart,
    required this.weekEnd,
    required this.completedSessions,
    required this.reviewedWords,
    required this.speakingAttempts,
    required this.weakItems,
    required this.recommendedActions,
    this.reportSummary = '',
    this.assetMastery = const <LearningAssetMastery>[],
    this.materialSummaries = const <MaterialReportSummary>[],
  });

  final List<LearningAssetMastery> assetMastery;
  final String childId;
  final int completedSessions;
  final String id;
  final List<MaterialReportSummary> materialSummaries;
  final List<String> recommendedActions;
  final String reportSummary;
  final int reviewedWords;
  final int speakingAttempts;
  final List<String> weakItems;
  final DateTime weekEnd;
  final DateTime weekStart;

  factory WeeklyReport.fromJson(JsonMap json) {
    return WeeklyReport(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      weekStart: dateTimeFromJson(json['week_start']) ?? DateTime.now(),
      weekEnd: dateTimeFromJson(json['week_end']) ?? DateTime.now(),
      completedSessions: json['completed_sessions'] as int? ?? 0,
      reviewedWords: json['reviewed_words'] as int? ?? 0,
      speakingAttempts: json['speaking_attempts'] as int? ?? 0,
      weakItems: stringListFromJson(json['weak_items']),
      recommendedActions: stringListFromJson(json['recommended_actions']),
      reportSummary: json['report_summary'] as String? ?? '',
      assetMastery: learningAssetMasteryFromJson(json['asset_mastery']),
      materialSummaries:
          materialReportSummariesFromJson(json['material_summaries']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'week_start': weekStart.toIso8601String(),
        'week_end': weekEnd.toIso8601String(),
        'completed_sessions': completedSessions,
        'reviewed_words': reviewedWords,
        'speaking_attempts': speakingAttempts,
        'weak_items': weakItems,
        'recommended_actions': recommendedActions,
        'report_summary': reportSummary,
        'asset_mastery': assetMastery.map((item) => item.toJson()).toList(),
        'material_summaries':
            materialSummaries.map((item) => item.toJson()).toList(),
      };
}
