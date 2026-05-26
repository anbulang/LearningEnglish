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
        payload['knowledge_pack'] as Map<String, dynamic>);
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
        .map((item) => ReviewTask.fromJson(item as Map<String, dynamic>))
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
    return WeeklyReport.fromJson(payload['report'] as Map<String, dynamic>);
  }

  Future<ChildProfile> createChild({
    required String name,
    required int age,
    required String level,
    required String learningGoal,
    required int preferredReviewDurationMinutes,
    required String parentNotes,
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
      return parsed
          .replace(
            scheme: apiBase.scheme,
            host: apiBase.host,
            port: apiBase.hasPort ? apiBase.port : null,
          )
          .toString();
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
}

class MaterialCreateResult {
  const MaterialCreateResult({
    required this.material,
    required this.job,
  });

  final MaterialParseJob job;
  final CourseMaterial material;
}
