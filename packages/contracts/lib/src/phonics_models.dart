import 'package:meta/meta.dart';

import 'enums.dart';
import 'json.dart';

/// Course + unit + progress models for the 自然拼读 (phonics) feature. These
/// mirror the FastAPI phonics contract 1:1 (see the ground-truth payloads under
/// scratchpad/phonics_api_payloads.json). Media/TTS status fields are kept as
/// plain strings to match [LearningAsset]'s tts_*_status convention; audio urls
/// are empty until seed-time TTS runs, so the UI must degrade gracefully.

@immutable
class PhonicsCourse {
  const PhonicsCourse({
    required this.id,
    required this.title,
    required this.description,
  });

  final String description;
  final String id;
  final String title;

  factory PhonicsCourse.fromJson(JsonMap json) {
    return PhonicsCourse(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'title': title,
        'description': description,
      };
}

/// One row in the unit list (`GET /phonics/units`). Carries the per-child
/// [status]/[decodingAccuracy] but not the resolved lesson content.
@immutable
class PhonicsUnitSummary {
  const PhonicsUnitSummary({
    required this.id,
    required this.unitCode,
    required this.sequenceOrder,
    required this.title,
    required this.subtitle,
    required this.level,
    required this.mediaStatus,
    required this.status,
    required this.decodingAccuracy,
  });

  final double decodingAccuracy;
  final String id;
  final String level;
  final String mediaStatus;
  final int sequenceOrder;
  final PhonicsUnitStatus status;
  final String subtitle;
  final String title;
  final String unitCode;

  factory PhonicsUnitSummary.fromJson(JsonMap json) {
    return PhonicsUnitSummary(
      id: json['id'] as String? ?? '',
      unitCode: json['unit_code'] as String? ?? '',
      sequenceOrder: json['sequence_order'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      level: json['level'] as String? ?? '',
      mediaStatus: json['media_status'] as String? ?? 'pending',
      status: PhonicsUnitStatus.fromJson(json['status'] as String? ?? 'locked'),
      decodingAccuracy: doubleFromJson(json['decoding_accuracy']) ?? 0,
    );
  }

  JsonMap toJson() => {
        'id': id,
        'unit_code': unitCode,
        'sequence_order': sequenceOrder,
        'title': title,
        'subtitle': subtitle,
        'level': level,
        'media_status': mediaStatus,
        'status': status.value,
        'decoding_accuracy': decodingAccuracy,
      };
}

@immutable
class PhonicsUnitListResponse {
  const PhonicsUnitListResponse({
    required this.course,
    required this.units,
    required this.nextUnitId,
  });

  final PhonicsCourse course;
  final String nextUnitId;
  final List<PhonicsUnitSummary> units;

  factory PhonicsUnitListResponse.fromJson(JsonMap json) {
    return PhonicsUnitListResponse(
      course: PhonicsCourse.fromJson(
          (json['course'] as JsonMap?) ?? const <String, dynamic>{}),
      units: (json['units'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsUnitSummary.fromJson)
          .toList(),
      nextUnitId: json['next_unit_id'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'course': course.toJson(),
        'units': units.map((unit) => unit.toJson()).toList(),
        'next_unit_id': nextUnitId,
      };
}

/// The resolved unit shell returned inside `GET /phonics/units/{id}`.
@immutable
class PhonicsUnit {
  const PhonicsUnit({
    required this.id,
    required this.unitCode,
    required this.sequenceOrder,
    required this.title,
    required this.subtitle,
    required this.level,
    required this.vowelFocus,
    required this.letters,
    required this.mediaStatus,
  });

  final String id;
  final List<String> letters;
  final String level;
  final String mediaStatus;
  final int sequenceOrder;
  final String subtitle;
  final String title;
  final String unitCode;
  final String vowelFocus;

  factory PhonicsUnit.fromJson(JsonMap json) {
    return PhonicsUnit(
      id: json['id'] as String? ?? '',
      unitCode: json['unit_code'] as String? ?? '',
      sequenceOrder: json['sequence_order'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      level: json['level'] as String? ?? '',
      vowelFocus: json['vowel_focus'] as String? ?? '',
      letters: stringListFromJson(json['letters']),
      mediaStatus: json['media_status'] as String? ?? 'pending',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'unit_code': unitCode,
        'sequence_order': sequenceOrder,
        'title': title,
        'subtitle': subtitle,
        'level': level,
        'vowel_focus': vowelFocus,
        'letters': letters,
        'media_status': mediaStatus,
      };
}

@immutable
class PhonicsExampleWord {
  const PhonicsExampleWord({
    required this.text,
    required this.cn,
  });

  final String cn;
  final String text;

  factory PhonicsExampleWord.fromJson(JsonMap json) {
    return PhonicsExampleWord(
      text: json['text'] as String? ?? '',
      cn: json['cn'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'text': text,
        'cn': cn,
      };
}

@immutable
class PhonicsSoundCard {
  const PhonicsSoundCard({
    required this.id,
    required this.cardType,
    required this.letter,
    required this.phoneme,
    required this.keyword,
    required this.keywordCn,
    required this.articulationCue,
    required this.commonSpellings,
    required this.speakableSound,
    required this.exampleWords,
    required this.soundAudioUrl,
    required this.soundTtsStatus,
    required this.keywordAudioUrl,
    required this.keywordTtsStatus,
  });

  final String articulationCue;
  final String cardType;
  final List<String> commonSpellings;
  final List<PhonicsExampleWord> exampleWords;
  final String id;
  final String keyword;
  final String keywordAudioUrl;
  final String keywordCn;
  final String keywordTtsStatus;
  final String letter;
  final String phoneme;
  final String soundAudioUrl;
  final String soundTtsStatus;
  final String speakableSound;

  bool get isVowel => cardType == 'vowel';

  factory PhonicsSoundCard.fromJson(JsonMap json) {
    return PhonicsSoundCard(
      id: json['id'] as String? ?? '',
      cardType: json['card_type'] as String? ?? 'consonant',
      letter: json['letter'] as String? ?? '',
      phoneme: json['phoneme'] as String? ?? '',
      keyword: json['keyword'] as String? ?? '',
      keywordCn: json['keyword_cn'] as String? ?? '',
      articulationCue: json['articulation_cue'] as String? ?? '',
      commonSpellings: stringListFromJson(json['common_spellings']),
      speakableSound: json['speakable_sound'] as String? ?? '',
      exampleWords: (json['example_words'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsExampleWord.fromJson)
          .toList(),
      soundAudioUrl: json['sound_audio_url'] as String? ?? '',
      soundTtsStatus: json['sound_tts_status'] as String? ?? 'pending',
      keywordAudioUrl: json['keyword_audio_url'] as String? ?? '',
      keywordTtsStatus: json['keyword_tts_status'] as String? ?? 'pending',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'card_type': cardType,
        'letter': letter,
        'phoneme': phoneme,
        'keyword': keyword,
        'keyword_cn': keywordCn,
        'articulation_cue': articulationCue,
        'common_spellings': commonSpellings,
        'speakable_sound': speakableSound,
        'example_words': exampleWords.map((word) => word.toJson()).toList(),
        'sound_audio_url': soundAudioUrl,
        'sound_tts_status': soundTtsStatus,
        'keyword_audio_url': keywordAudioUrl,
        'keyword_tts_status': keywordTtsStatus,
      };
}

@immutable
class PhonicsDecodableWord {
  const PhonicsDecodableWord({
    required this.id,
    required this.text,
    required this.segments,
    required this.cn,
    required this.kind,
    required this.audioUrl,
    required this.ttsStatus,
  });

  final String audioUrl;
  final String cn;
  final String id;
  final String kind;
  final List<String> segments;
  final String text;
  final String ttsStatus;

  factory PhonicsDecodableWord.fromJson(JsonMap json) {
    return PhonicsDecodableWord(
      id: json['id'] as String? ?? '',
      text: json['text'] as String? ?? '',
      segments: stringListFromJson(json['segments']),
      cn: json['cn'] as String? ?? '',
      kind: json['kind'] as String? ?? 'real',
      audioUrl: json['audio_url'] as String? ?? '',
      ttsStatus: json['tts_status'] as String? ?? 'pending',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'text': text,
        'segments': segments,
        'cn': cn,
        'kind': kind,
        'audio_url': audioUrl,
        'tts_status': ttsStatus,
      };
}

@immutable
class PhonicsSentence {
  const PhonicsSentence({
    required this.id,
    required this.text,
    required this.cn,
    required this.audioUrl,
    required this.ttsStatus,
  });

  final String audioUrl;
  final String cn;
  final String id;
  final String text;
  final String ttsStatus;

  factory PhonicsSentence.fromJson(JsonMap json) {
    return PhonicsSentence(
      id: json['id'] as String? ?? '',
      text: json['text'] as String? ?? '',
      cn: json['cn'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      ttsStatus: json['tts_status'] as String? ?? 'pending',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'text': text,
        'cn': cn,
        'audio_url': audioUrl,
        'tts_status': ttsStatus,
      };
}

@immutable
class PhonicsHeartWord {
  const PhonicsHeartWord({
    required this.text,
    required this.cn,
    required this.audioUrl,
    required this.ttsStatus,
  });

  final String audioUrl;
  final String cn;
  final String text;
  final String ttsStatus;

  factory PhonicsHeartWord.fromJson(JsonMap json) {
    return PhonicsHeartWord(
      text: json['text'] as String? ?? '',
      cn: json['cn'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      ttsStatus: json['tts_status'] as String? ?? 'pending',
    );
  }

  JsonMap toJson() => {
        'text': text,
        'cn': cn,
        'audio_url': audioUrl,
        'tts_status': ttsStatus,
      };
}

@immutable
class PhonicsFirstSoundItem {
  const PhonicsFirstSoundItem({
    required this.id,
    required this.wordId,
    required this.text,
    required this.cn,
    required this.answer,
    required this.options,
    required this.audioUrl,
  });

  final String answer;
  final String audioUrl;
  final String cn;
  final String id;
  final List<String> options;
  final String text;
  final String wordId;

  factory PhonicsFirstSoundItem.fromJson(JsonMap json) {
    return PhonicsFirstSoundItem(
      id: json['id'] as String? ?? '',
      wordId: json['word_id'] as String? ?? '',
      text: json['text'] as String? ?? '',
      cn: json['cn'] as String? ?? '',
      answer: json['answer'] as String? ?? '',
      options: stringListFromJson(json['options']),
      audioUrl: json['audio_url'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'id': id,
        'word_id': wordId,
        'text': text,
        'cn': cn,
        'answer': answer,
        'options': options,
        'audio_url': audioUrl,
      };
}

@immutable
class PhonicsStep {
  const PhonicsStep({
    required this.key,
    required this.practiceType,
    required this.title,
    required this.instruction,
    required this.cardIds,
    required this.wordIds,
    required this.itemIds,
    required this.heartWords,
  });

  final List<String> cardIds;
  final List<String> heartWords;
  final String instruction;
  final List<String> itemIds;
  final String key;
  final PhonicsPracticeType practiceType;
  final String title;
  final List<String> wordIds;

  factory PhonicsStep.fromJson(JsonMap json) {
    return PhonicsStep(
      key: json['key'] as String? ?? '',
      practiceType:
          PhonicsPracticeType.fromJson(json['practice_type'] as String? ?? 'none'),
      title: json['title'] as String? ?? '',
      instruction: json['instruction'] as String? ?? '',
      cardIds: stringListFromJson(json['card_ids']),
      wordIds: stringListFromJson(json['word_ids']),
      itemIds: stringListFromJson(json['item_ids']),
      heartWords: stringListFromJson(json['heart_words']),
    );
  }

  JsonMap toJson() => {
        'key': key,
        'practice_type': practiceType.value,
        'title': title,
        'instruction': instruction,
        'card_ids': cardIds,
        'word_ids': wordIds,
        'item_ids': itemIds,
        'heart_words': heartWords,
      };
}

@immutable
class PhonicsProgress {
  const PhonicsProgress({
    required this.unitId,
    required this.status,
    required this.decodingAccuracy,
    required this.firstSoundAccuracy,
    required this.graphemeScores,
    required this.attemptsCount,
    required this.blendedWords,
    required this.mastered,
  });

  final int attemptsCount;
  final List<String> blendedWords;
  final double decodingAccuracy;
  final double firstSoundAccuracy;
  final Map<String, double> graphemeScores;
  final bool mastered;
  final PhonicsUnitStatus status;
  final String unitId;

  factory PhonicsProgress.fromJson(JsonMap json) {
    return PhonicsProgress(
      unitId: json['unit_id'] as String? ?? '',
      status: PhonicsUnitStatus.fromJson(json['status'] as String? ?? 'locked'),
      decodingAccuracy: doubleFromJson(json['decoding_accuracy']) ?? 0,
      firstSoundAccuracy: doubleFromJson(json['first_sound_accuracy']) ?? 0,
      graphemeScores: _graphemeScoresFromJson(json['grapheme_scores']),
      attemptsCount: json['attempts_count'] as int? ?? 0,
      blendedWords: stringListFromJson(json['blended_words']),
      mastered: json['mastered'] as bool? ?? false,
    );
  }

  JsonMap toJson() => {
        'unit_id': unitId,
        'status': status.value,
        'decoding_accuracy': decodingAccuracy,
        'first_sound_accuracy': firstSoundAccuracy,
        'grapheme_scores': graphemeScores,
        'attempts_count': attemptsCount,
        'blended_words': blendedWords,
        'mastered': mastered,
      };
}

Map<String, double> _graphemeScoresFromJson(dynamic value) {
  if (value is! Map) {
    return const <String, double>{};
  }
  final result = <String, double>{};
  value.forEach((key, dynamic score) {
    final parsed = doubleFromJson(score);
    if (parsed != null) {
      result[key.toString()] = parsed;
    }
  });
  return result;
}

@immutable
class PhonicsUnitDetailResponse {
  const PhonicsUnitDetailResponse({
    required this.unit,
    required this.soundCards,
    required this.decodableWords,
    required this.sentences,
    required this.heartWords,
    required this.firstSoundItems,
    required this.steps,
    required this.progress,
  });

  final List<PhonicsDecodableWord> decodableWords;
  final List<PhonicsFirstSoundItem> firstSoundItems;
  final List<PhonicsHeartWord> heartWords;
  final PhonicsProgress progress;
  final List<PhonicsSentence> sentences;
  final List<PhonicsSoundCard> soundCards;
  final List<PhonicsStep> steps;
  final PhonicsUnit unit;

  factory PhonicsUnitDetailResponse.fromJson(JsonMap json) {
    return PhonicsUnitDetailResponse(
      unit: PhonicsUnit.fromJson(
          (json['unit'] as JsonMap?) ?? const <String, dynamic>{}),
      soundCards:
          (json['sound_cards'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<JsonMap>()
              .map(PhonicsSoundCard.fromJson)
              .toList(),
      decodableWords:
          (json['decodable_words'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<JsonMap>()
              .map(PhonicsDecodableWord.fromJson)
              .toList(),
      sentences: (json['sentences'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsSentence.fromJson)
          .toList(),
      heartWords: (json['heart_words'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsHeartWord.fromJson)
          .toList(),
      firstSoundItems:
          (json['first_sound_items'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<JsonMap>()
              .map(PhonicsFirstSoundItem.fromJson)
              .toList(),
      steps: (json['steps'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsStep.fromJson)
          .toList(),
      progress: PhonicsProgress.fromJson(
          (json['progress'] as JsonMap?) ?? const <String, dynamic>{}),
    );
  }

  JsonMap toJson() => {
        'unit': unit.toJson(),
        'sound_cards': soundCards.map((card) => card.toJson()).toList(),
        'decodable_words':
            decodableWords.map((word) => word.toJson()).toList(),
        'sentences': sentences.map((sentence) => sentence.toJson()).toList(),
        'heart_words': heartWords.map((word) => word.toJson()).toList(),
        'first_sound_items':
            firstSoundItems.map((item) => item.toJson()).toList(),
        'steps': steps.map((step) => step.toJson()).toList(),
        'progress': progress.toJson(),
      };
}

/// One tap/choice result row posted to `POST /phonics/attempts` and echoed back
/// on the scored attempt.
@immutable
class PhonicsItemResult {
  const PhonicsItemResult({
    required this.prompt,
    required this.expected,
    required this.given,
    required this.correct,
  });

  final bool correct;
  final String expected;
  final String given;
  final String prompt;

  factory PhonicsItemResult.fromJson(JsonMap json) {
    return PhonicsItemResult(
      prompt: json['prompt'] as String? ?? '',
      expected: json['expected'] as String? ?? '',
      given: json['given'] as String? ?? '',
      correct: json['correct'] as bool? ?? false,
    );
  }

  JsonMap toJson() => {
        'prompt': prompt,
        'expected': expected,
        'given': given,
        'correct': correct,
      };
}

@immutable
class PhonicsAttempt {
  const PhonicsAttempt({
    required this.id,
    required this.childId,
    required this.unitId,
    required this.step,
    required this.practiceType,
    required this.targetText,
    required this.itemResults,
    required this.accuracyScore,
    required this.passed,
    required this.transcript,
    required this.feedback,
    required this.audioUrl,
    required this.provider,
    required this.failureReason,
    required this.status,
    this.createdAt,
    this.updatedAt,
  });

  final double? accuracyScore;
  final String audioUrl;
  final String childId;
  final DateTime? createdAt;
  final String failureReason;
  final String feedback;
  final String id;
  final List<PhonicsItemResult> itemResults;
  final bool passed;
  final PhonicsPracticeType practiceType;
  final String provider;
  final PhonicsAttemptStatus status;
  final String step;
  final String targetText;
  final String transcript;
  final String unitId;
  final DateTime? updatedAt;

  factory PhonicsAttempt.fromJson(JsonMap json) {
    return PhonicsAttempt(
      id: json['id'] as String? ?? '',
      childId: json['child_id'] as String? ?? '',
      unitId: json['unit_id'] as String? ?? '',
      step: json['step'] as String? ?? '',
      practiceType:
          PhonicsPracticeType.fromJson(json['practice_type'] as String? ?? 'none'),
      targetText: json['target_text'] as String? ?? '',
      itemResults:
          (json['item_results'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<JsonMap>()
              .map(PhonicsItemResult.fromJson)
              .toList(),
      accuracyScore: doubleFromJson(json['accuracy_score']),
      passed: json['passed'] as bool? ?? false,
      transcript: json['transcript'] as String? ?? '',
      feedback: json['feedback'] as String? ?? '',
      audioUrl: json['audio_url'] as String? ?? '',
      provider: json['provider'] as String? ?? '',
      failureReason: json['failure_reason'] as String? ?? '',
      status:
          PhonicsAttemptStatus.fromJson(json['status'] as String? ?? 'queued'),
      createdAt: dateTimeFromJson(json['created_at']),
      updatedAt: dateTimeFromJson(json['updated_at']),
    );
  }

  JsonMap toJson() => {
        'id': id,
        'child_id': childId,
        'unit_id': unitId,
        'step': step,
        'practice_type': practiceType.value,
        'target_text': targetText,
        'item_results': itemResults.map((item) => item.toJson()).toList(),
        'accuracy_score': accuracyScore,
        'passed': passed,
        'transcript': transcript,
        'feedback': feedback,
        'audio_url': audioUrl,
        'provider': provider,
        'failure_reason': failureReason,
        'status': status.value,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };
}

@immutable
class PhonicsAttemptResponse {
  const PhonicsAttemptResponse({
    required this.attempt,
    required this.progress,
  });

  final PhonicsAttempt attempt;
  final PhonicsProgress progress;

  factory PhonicsAttemptResponse.fromJson(JsonMap json) {
    return PhonicsAttemptResponse(
      attempt: PhonicsAttempt.fromJson(
          (json['attempt'] as JsonMap?) ?? const <String, dynamic>{}),
      progress: PhonicsProgress.fromJson(
          (json['progress'] as JsonMap?) ?? const <String, dynamic>{}),
    );
  }

  JsonMap toJson() => {
        'attempt': attempt.toJson(),
        'progress': progress.toJson(),
      };
}

@immutable
class PhonicsProgressResponse {
  const PhonicsProgressResponse({
    required this.course,
    required this.units,
    required this.nextUnitId,
    required this.masteredCount,
    required this.totalUnits,
  });

  final PhonicsCourse course;
  final int masteredCount;
  final String nextUnitId;
  final int totalUnits;
  final List<PhonicsProgress> units;

  factory PhonicsProgressResponse.fromJson(JsonMap json) {
    return PhonicsProgressResponse(
      course: PhonicsCourse.fromJson(
          (json['course'] as JsonMap?) ?? const <String, dynamic>{}),
      units: (json['units'] as List<dynamic>? ?? const <dynamic>[])
          .whereType<JsonMap>()
          .map(PhonicsProgress.fromJson)
          .toList(),
      nextUnitId: json['next_unit_id'] as String? ?? '',
      masteredCount: json['mastered_count'] as int? ?? 0,
      totalUnits: json['total_units'] as int? ?? 0,
    );
  }

  JsonMap toJson() => {
        'course': course.toJson(),
        'units': units.map((unit) => unit.toJson()).toList(),
        'next_unit_id': nextUnitId,
        'mastered_count': masteredCount,
        'total_units': totalUnits,
      };
}
