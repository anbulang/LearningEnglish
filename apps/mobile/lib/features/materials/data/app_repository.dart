import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

import '../../../core/network/api_client.dart';
import '../../session/data/session_controller.dart'
    show sessionControllerProvider;
import 'materials_repository.dart';
import 'scan_draft_controller.dart';

final appRepositoryProvider = Provider<AppRepository>((ref) {
  return AppRepository(
    ref.watch(apiClientProvider).raw,
    accessToken: () => ref.read(sessionControllerProvider).accessToken,
    refreshSession:
        ref.watch(sessionControllerProvider.notifier).refreshSession,
  );
});

class AppRepository implements MaterialsRepository {
  AppRepository(
    this._dio, {
    required String? Function() accessToken,
    required Future<bool> Function() refreshSession,
  })  : _accessToken = accessToken,
        _refreshSession = refreshSession;

  final String? Function() _accessToken;
  final Dio _dio;
  final Future<bool> Function() _refreshSession;

  Options get _options => Options(
        headers: <String, dynamic>{
          if (_accessToken() != null)
            'Authorization': 'Bearer ${_accessToken()}',
        },
      );

  bool _isUnauthorized(DioException error) => error.response?.statusCode == 401;

  Future<Response<T>> _authorizedRequest<T>(
    Future<Response<T>> Function(Options options) send,
  ) async {
    try {
      return await send(_options);
    } on DioException catch (error) {
      if (!_isUnauthorized(error)) {
        rethrow;
      }
      final refreshed = await _refreshSession();
      if (!refreshed) {
        rethrow;
      }
      return send(_options);
    }
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/knowledge-packs/$materialId',
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return KnowledgePack.fromJson(
      _normalizeKnowledgePackRuntimeUrls(
          payload['knowledge_pack'] as Map<String, dynamic>),
    );
  }

  @override
  Future<MaterialParseJob> getMaterialJob(String jobId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/material-jobs/$jobId',
        options: options,
      ),
    );
    return _materialParseJobFromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<ParentCoachingScript> getParentCoaching(String materialId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/parent-coaching/$materialId',
        options: options,
      ),
    );
    return ParentCoachingScript.fromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<CourseMaterial> getMaterial(String materialId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/materials/$materialId',
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return _courseMaterialFromJson(payload['material'] as Map<String, dynamic>);
  }

  @override
  Future<List<CourseMaterial>> listMaterials({required String childId}) async {
    final response = await _authorizedRequest<List<dynamic>>(
      (options) => _dio.get<List<dynamic>>(
        '/materials',
        queryParameters: <String, dynamic>{'child_id': childId},
        options: options,
      ),
    );
    return (response.data ?? const <dynamic>[])
        .map((item) => _courseMaterialFromJson(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> deleteMaterial(String materialId) async {
    await _authorizedRequest<void>(
      (options) => _dio.delete<void>(
        '/materials/$materialId',
        options: options,
      ),
    );
  }

  @override
  Future<List<ReviewTask>> listReviewTasks({
    required String childId,
    String? materialId,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/review-tasks',
        queryParameters: <String, dynamic>{
          'child_id': childId,
          if (materialId != null) 'material_id': materialId,
        },
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return (payload['items'] as List<dynamic>? ?? const <dynamic>[])
        .map((item) => ReviewTask.fromJson(
            _normalizeReviewTaskRuntimeUrls(item as Map<String, dynamic>)))
        .toList();
  }

  Future<WeeklyReport> getWeeklyReport({required String childId}) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/reports/weekly',
        queryParameters: <String, dynamic>{'child_id': childId},
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return WeeklyReport.fromJson(
      _normalizeWeeklyReportRuntimeUrls(
          payload['report'] as Map<String, dynamic>),
    );
  }

  Future<ChildProfile> createChild({
    required String name,
    required int age,
    required String level,
    required String learningGoal,
    required int preferredReviewDurationMinutes,
    required String parentNotes,
    String accent = 'us',
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/children',
        data: <String, dynamic>{
          'name': name,
          'age': age,
          'level': level,
          'learning_goal': learningGoal,
          'preferred_review_duration_minutes': preferredReviewDurationMinutes,
          'parent_notes': parentNotes,
          'accent': accent,
        },
        options: options,
      ),
    );
    return ChildProfile.fromJson(response.data ?? const <String, dynamic>{});
  }

  /// Partially updates a child profile. Only the non-null fields are sent, so
  /// the backend leaves everything else untouched. Returns the updated
  /// [ChildProfile].
  Future<ChildProfile> updateChild({
    required String childId,
    String? accent,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.patch<Map<String, dynamic>>(
        '/children/$childId',
        data: <String, dynamic>{
          if (accent != null) 'accent': accent,
        },
        options: options,
      ),
    );
    return ChildProfile.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<MaterialCreateResult> uploadMaterial({
    required String childId,
    required String teacherName,
    required DateTime lessonDate,
    required String title,
    required String topic,
    required List<ScanDraftPage> files,
  }) async {
    Future<FormData> buildFormData() async {
      final safeTitle = title.trim().isEmpty ? '待识别讲义' : title.trim();
      final safeTeacherName =
          teacherName.trim().isEmpty ? '外教课' : teacherName.trim();
      final safeTopic = topic.trim();
      return FormData.fromMap(<String, dynamic>{
        'child_id': childId,
        'teacher_name': safeTeacherName,
        'lesson_date': lessonDate.toIso8601String().split('T').first,
        'title': safeTitle,
        'topic': safeTopic,
        'tags': safeTopic,
        'file_sources': [for (final file in files) file.sourceType],
        'files': [
          for (final file in files)
            await MultipartFile.fromFile(
              file.file.path,
              filename: file.file.name,
            ),
        ],
      });
    }

    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) async => _dio.post<Map<String, dynamic>>(
        '/materials',
        data: await buildFormData(),
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return MaterialCreateResult(
      material:
          _courseMaterialFromJson(payload['material'] as Map<String, dynamic>),
      job: _materialParseJobFromJson(payload['job'] as Map<String, dynamic>),
    );
  }

  CourseMaterial _courseMaterialFromJson(Map<String, dynamic> json) {
    return CourseMaterial.fromJson(_normalizeMaterialRuntimeUrls(json));
  }

  MaterialParseJob _materialParseJobFromJson(Map<String, dynamic> json) {
    return MaterialParseJob.fromJson(_normalizeJobRuntimeUrls(json));
  }

  Map<String, dynamic> _normalizeMaterialRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    normalized['source_images'] =
        _normalizeStringUrls(normalized['source_images']);
    final records = normalized['image_records'];
    if (records is List) {
      normalized['image_records'] = records.map((record) {
        if (record is! Map<String, dynamic>) {
          return record;
        }
        final normalizedRecord = Map<String, dynamic>.from(record);
        normalizedRecord['url'] =
            _publicRuntimeUrl(normalizedRecord['url'] as String? ?? '');
        return normalizedRecord;
      }).toList();
    }
    normalized['learning_assets'] =
        _normalizeLearningAssetUrls(normalized['learning_assets']);
    return normalized;
  }

  Map<String, dynamic> _normalizeJobRuntimeUrls(Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    final records = normalized['draft_image_records'];
    if (records is List) {
      normalized['draft_image_records'] = records.map((record) {
        if (record is! Map<String, dynamic>) {
          return record;
        }
        final normalizedRecord = Map<String, dynamic>.from(record);
        normalizedRecord['url'] =
            _publicRuntimeUrl(normalizedRecord['url'] as String? ?? '');
        return normalizedRecord;
      }).toList();
    }
    normalized['draft_learning_assets'] =
        _normalizeLearningAssetUrls(normalized['draft_learning_assets']);
    return normalized;
  }

  Map<String, dynamic> _normalizeWeeklyReportRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    final mastery = normalized['asset_mastery'];
    if (mastery is List) {
      normalized['asset_mastery'] = mastery.map((item) {
        if (item is! Map<String, dynamic>) {
          return item;
        }
        final normalizedItem = Map<String, dynamic>.from(item);
        normalizedItem['image_url'] =
            _publicRuntimeUrl(normalizedItem['image_url'] as String? ?? '');
        normalizedItem['audio_url'] =
            _publicRuntimeUrl(normalizedItem['audio_url'] as String? ?? '');
        return normalizedItem;
      }).toList();
    }
    return normalized;
  }

  Map<String, dynamic> _normalizeKnowledgePackRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    normalized['vocabulary_items'] =
        _normalizeAudioImageUrls(normalized['vocabulary_items']);
    normalized['sentence_patterns'] =
        _normalizeAudioImageUrls(normalized['sentence_patterns']);
    return normalized;
  }

  Map<String, dynamic> _normalizeReviewTaskRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    final content = normalized['content_json'];
    if (content is Map<String, dynamic>) {
      final normalizedContent = Map<String, dynamic>.from(content);
      for (final key in <String>['audio_url', 'image_url']) {
        if (normalizedContent.containsKey(key)) {
          normalizedContent[key] =
              _publicRuntimeUrl(normalizedContent[key] as String? ?? '');
        }
      }
      normalized['content_json'] = normalizedContent;
    }
    return normalized;
  }

  dynamic _normalizeAudioImageUrls(dynamic value) {
    if (value is! List) {
      return value;
    }
    return value.map((item) {
      if (item is! Map<String, dynamic>) {
        return item;
      }
      final normalizedItem = Map<String, dynamic>.from(item);
      for (final key in <String>['audio_url', 'image_url']) {
        if (normalizedItem.containsKey(key)) {
          normalizedItem[key] =
              _publicRuntimeUrl(normalizedItem[key] as String? ?? '');
        }
      }
      return normalizedItem;
    }).toList();
  }

  dynamic _normalizeLearningAssetUrls(dynamic value) {
    if (value is! List) {
      return value;
    }
    return value.map((asset) {
      if (asset is! Map<String, dynamic>) {
        return asset;
      }
      final normalizedAsset = Map<String, dynamic>.from(asset);
      for (final key in <String>[
        'generated_image_url',
        'tts_us_url',
        'tts_uk_url',
      ]) {
        normalizedAsset[key] =
            _publicRuntimeUrl(normalizedAsset[key] as String? ?? '');
      }
      return normalizedAsset;
    }).toList();
  }

  List<String> _normalizeStringUrls(dynamic value) {
    if (value is! List) {
      return const <String>[];
    }
    return value
        .whereType<String>()
        .map(_publicRuntimeUrl)
        .toList(growable: false);
  }

  String _publicRuntimeUrl(String url) {
    final parsed = Uri.tryParse(url);
    if (parsed == null) {
      return url;
    }
    final apiBase = Uri.parse(_dio.options.baseUrl);
    if (parsed.host == 'minio') {
      final segments = parsed.pathSegments;
      if (segments.length < 2) {
        return url;
      }
      return apiBase.replace(
        pathSegments: <String>['uploads', ...segments.skip(1)],
        queryParameters: null,
        fragment: null,
      ).toString();
    }
    if (parsed.host == 'localhost') {
      final firstSegment =
          parsed.pathSegments.isEmpty ? '' : parsed.pathSegments.first;
      if (firstSegment != 'uploads' && firstSegment != 'mock-media') {
        return url;
      }
      // Rebuild via the Uri constructor: on `replace`, a null port means "keep
      // the original" — which would leave the stale localhost :9000 on a real
      // host. The constructor treats null port as "no port" so a portless public
      // base (https://api.example.com) yields https://api.example.com/uploads/...
      return Uri(
        scheme: apiBase.scheme,
        host: apiBase.host,
        port: apiBase.hasPort ? apiBase.port : null,
        path: parsed.path,
        query: parsed.hasQuery ? parsed.query : null,
      ).toString();
    }
    return url;
  }

  Future<MaterialParseJob> confirmMaterialJob({
    required String jobId,
    required String draftTitle,
    required String draftTopic,
    required List<String> draftVocabulary,
    required List<String> draftSentences,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/material-jobs/$jobId/confirm',
        data: <String, dynamic>{
          'draft_title': draftTitle,
          'draft_topic': draftTopic,
          'draft_vocabulary': draftVocabulary,
          'draft_sentences': draftSentences,
        },
        options: options,
      ),
    );
    return _materialParseJobFromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<CourseMaterial> updateLearningAssetPrimaryAccent({
    required String materialId,
    required String assetId,
    required String primaryAccent,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.patch<Map<String, dynamic>>(
        '/materials/$materialId/learning-assets/$assetId/primary-accent',
        data: <String, dynamic>{'primary_accent': primaryAccent},
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return _courseMaterialFromJson(payload['material'] as Map<String, dynamic>);
  }

  Future<MaterialParseJob> retryMaterialJob({
    required String jobId,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/material-jobs/$jobId/retry',
        options: options,
      ),
    );
    return _materialParseJobFromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<PracticeSession> createPracticeSession({
    required String childId,
    required List<String> reviewTaskIds,
    required double score,
    required List<String> weakPoints,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/practice-sessions',
        data: <String, dynamic>{
          'child_id': childId,
          'review_task_ids': reviewTaskIds,
          'score': score,
          'weak_points': weakPoints,
        },
        options: options,
      ),
    );
    return PracticeSession.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<SpeakingAttempt> uploadSpeakingAttempt({
    required String childId,
    required String materialId,
    required String promptText,
    required String targetText,
    required String audioPath,
    String reviewTaskId = '',
    String learningAssetId = '',
    int audioDurationMs = 0,
  }) async {
    Future<FormData> buildForm() async {
      return FormData.fromMap(<String, dynamic>{
        'child_id': childId,
        'material_id': materialId,
        'prompt_text': promptText,
        'target_text': targetText,
        'review_task_id': reviewTaskId,
        'learning_asset_id': learningAssetId,
        'audio_duration_ms': audioDurationMs,
        'audio': await MultipartFile.fromFile(
          audioPath,
          filename: 'speaking-attempt.m4a',
          contentType: DioMediaType('audio', 'mp4'),
        ),
      });
    }

    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) async {
        return _dio.post<Map<String, dynamic>>(
          '/speaking-attempts',
          data: await buildForm(),
          options: options,
        );
      },
    );
    return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<SpeakingAttempt> getSpeakingAttempt(String attemptId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/speaking-attempts/$attemptId',
        options: options,
      ),
    );
    return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<SpeakingAttempt> retrySpeakingAttempt(String attemptId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/speaking-attempts/$attemptId/retry',
        options: options,
      ),
    );
    return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
  }

  // --- 自然拼读 (phonics) ---------------------------------------------------

  Future<PhonicsUnitListResponse> getPhonicsUnits(String childId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/phonics/units',
        queryParameters: <String, dynamic>{'child_id': childId},
        options: options,
      ),
    );
    // Unit summaries carry no media urls, so no normalization is needed here.
    return PhonicsUnitListResponse.fromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<PhonicsUnitDetailResponse> getPhonicsUnit(
    String unitId,
    String childId,
  ) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/phonics/units/$unitId',
        queryParameters: <String, dynamic>{'child_id': childId},
        options: options,
      ),
    );
    return PhonicsUnitDetailResponse.fromJson(
      _normalizePhonicsUnitDetailRuntimeUrls(
          response.data ?? const <String, dynamic>{}),
    );
  }

  Future<PhonicsProgressResponse> getPhonicsProgress(String childId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/phonics/progress',
        queryParameters: <String, dynamic>{'child_id': childId},
        options: options,
      ),
    );
    return PhonicsProgressResponse.fromJson(
        response.data ?? const <String, dynamic>{});
  }

  Future<PhonicsAttemptResponse> submitPhonicsTapAttempt({
    required String childId,
    required String unitId,
    required String step,
    required String practiceType,
    required List<PhonicsItemResult> itemResults,
  }) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.post<Map<String, dynamic>>(
        '/phonics/attempts',
        data: <String, dynamic>{
          'child_id': childId,
          'unit_id': unitId,
          'step': step,
          'practice_type': practiceType,
          'item_results':
              itemResults.map((item) => item.toJson()).toList(),
        },
        options: options,
      ),
    );
    final payload = response.data ?? const <String, dynamic>{};
    final normalized = Map<String, dynamic>.from(payload);
    final attempt = normalized['attempt'];
    if (attempt is Map<String, dynamic>) {
      normalized['attempt'] = _normalizePhonicsAttemptRuntimeUrls(attempt);
    }
    return PhonicsAttemptResponse.fromJson(normalized);
  }

  Future<PhonicsAttempt> uploadPhonicsWordAttempt({
    required String childId,
    required String unitId,
    required String targetText,
    required String filePath,
    int durationMs = 0,
    String step = 'blending',
  }) async {
    Future<FormData> buildForm() async {
      return FormData.fromMap(<String, dynamic>{
        'child_id': childId,
        'unit_id': unitId,
        'target_text': targetText,
        'step': step,
        'audio_duration_ms': durationMs,
        'audio': await MultipartFile.fromFile(
          filePath,
          filename: 'phonics-attempt.m4a',
          contentType: DioMediaType('audio', 'mp4'),
        ),
      });
    }

    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) async {
        return _dio.post<Map<String, dynamic>>(
          '/phonics/attempts/audio',
          data: await buildForm(),
          options: options,
        );
      },
    );
    return PhonicsAttempt.fromJson(
      _normalizePhonicsAttemptRuntimeUrls(
          response.data ?? const <String, dynamic>{}),
    );
  }

  Future<PhonicsAttempt> getPhonicsAttempt(String attemptId) async {
    final response = await _authorizedRequest<Map<String, dynamic>>(
      (options) => _dio.get<Map<String, dynamic>>(
        '/phonics/attempts/$attemptId',
        options: options,
      ),
    );
    return PhonicsAttempt.fromJson(
      _normalizePhonicsAttemptRuntimeUrls(
          response.data ?? const <String, dynamic>{}),
    );
  }

  Map<String, dynamic> _normalizePhonicsUnitDetailRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    normalized['sound_cards'] = _normalizePhonicsUrls(
      normalized['sound_cards'],
      const <String>['sound_audio_url', 'keyword_audio_url'],
    );
    normalized['decodable_words'] = _normalizePhonicsUrls(
      normalized['decodable_words'],
      const <String>['audio_url'],
    );
    normalized['sentences'] = _normalizePhonicsUrls(
      normalized['sentences'],
      const <String>['audio_url'],
    );
    normalized['heart_words'] = _normalizePhonicsUrls(
      normalized['heart_words'],
      const <String>['audio_url'],
    );
    normalized['first_sound_items'] = _normalizePhonicsUrls(
      normalized['first_sound_items'],
      const <String>['audio_url'],
    );
    return normalized;
  }

  Map<String, dynamic> _normalizePhonicsAttemptRuntimeUrls(
      Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    normalized['audio_url'] =
        _publicRuntimeUrl(normalized['audio_url'] as String? ?? '');
    return normalized;
  }

  dynamic _normalizePhonicsUrls(dynamic value, List<String> keys) {
    if (value is! List) {
      return value;
    }
    return value.map((item) {
      if (item is! Map<String, dynamic>) {
        return item;
      }
      final normalizedItem = Map<String, dynamic>.from(item);
      for (final key in keys) {
        if (normalizedItem.containsKey(key)) {
          normalizedItem[key] =
              _publicRuntimeUrl(normalizedItem[key] as String? ?? '');
        }
      }
      return normalizedItem;
    }).toList();
  }
}

class MaterialCreateResult {
  const MaterialCreateResult({
    required this.material,
    required this.job,
  });

  final MaterialParseJob job;
  final CourseMaterial material;
}
