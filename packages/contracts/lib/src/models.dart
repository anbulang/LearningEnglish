import 'package:meta/meta.dart';

import 'enums.dart';
import 'json.dart';

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
  });

  final String id;
  final String avatarUrl;
  final int age;
  final String learningGoal;
  final String level;
  final String name;
  final String parentNotes;
  final int preferredReviewDurationMinutes;

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
      };
}

@immutable
class CourseMaterial {
  const CourseMaterial({
    required this.id,
    required this.childId,
    required this.teacherName,
    required this.lessonDate,
    required this.title,
    required this.topic,
    required this.status,
    required this.sourceImages,
    required this.pdfUrl,
    required this.ocrText,
    required this.tags,
  });

  final String childId;
  final String id;
  final DateTime lessonDate;
  final String ocrText;
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
      teacherName: json['teacher_name'] as String? ?? '',
      lessonDate: dateTimeFromJson(json['lesson_date']) ?? DateTime.now(),
      title: json['title'] as String,
      topic: json['topic'] as String? ?? '',
      status: MaterialStatus.fromJson(json['status'] as String),
      sourceImages: stringListFromJson(json['source_images']),
      pdfUrl: json['pdf_url'] as String? ?? '',
      ocrText: json['ocr_text'] as String? ?? '',
      tags: stringListFromJson(json['tags']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'teacher_name': teacherName,
        'lesson_date': lessonDate.toIso8601String(),
        'title': title,
        'topic': topic,
        'status': status.value,
        'source_images': sourceImages,
        'pdf_url': pdfUrl,
        'ocr_text': ocrText,
        'tags': tags,
      };
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
  });

  final String confidenceSummary;
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
        'vocabulary_items': vocabularyItems.map((item) => item.toJson()).toList(),
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
  });

  final String audioUrl;
  final String childId;
  final String feedback;
  final String id;
  final String materialId;
  final String promptText;
  final double? pronunciationScore;
  final SpeakingAttemptStatus status;
  final String transcript;

  factory SpeakingAttempt.fromJson(JsonMap json) {
    return SpeakingAttempt(
      id: json['id'] as String,
      childId: json['child_id'] as String,
      materialId: json['material_id'] as String,
      promptText: json['prompt_text'] as String,
      audioUrl: json['audio_url'] as String? ?? '',
      transcript: json['transcript'] as String? ?? '',
      pronunciationScore: doubleFromJson(json['pronunciation_score']),
      feedback: json['feedback'] as String? ?? '',
      status: SpeakingAttemptStatus.fromJson(json['status'] as String),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'material_id': materialId,
        'prompt_text': promptText,
        'audio_url': audioUrl,
        'transcript': transcript,
        'pronunciation_score': pronunciationScore,
        'feedback': feedback,
        'status': status.value,
      };
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
  });

  final String childId;
  final int completedSessions;
  final String id;
  final List<String> recommendedActions;
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
      };
}
