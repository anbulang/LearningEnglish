import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import 'package:learning_english_mobile/core/theme/app_theme.dart';

const _apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000/v1',
);

const _sourceImageUrlsValue = String.fromEnvironment('SOURCE_IMAGE_URLS');

void main() {
  runApp(const _HarnessApp());
}

class _HarnessApp extends StatelessWidget {
  const _HarnessApp();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const _HarnessScreen(),
    );
  }
}

class _HarnessScreen extends StatefulWidget {
  const _HarnessScreen();

  @override
  State<_HarnessScreen> createState() => _HarnessScreenState();
}

class _HarnessScreenState extends State<_HarnessScreen> {
  final List<String> _logs = <String>[];
  Map<String, dynamic>? _summary;
  String? _error;
  bool _running = true;

  @override
  void initState() {
    super.initState();
    unawaited(_run());
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    return Scaffold(
      appBar: AppBar(title: const Text('HN-019 真机主链验证')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: <Widget>[
            Text(
              _running ? '正在执行真机主链...' : '真机主链执行完成',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: Colors.red)),
            if (summary != null) ...<Widget>[
              Text('标题：${summary['title']}'),
              Text('Material：${summary['material_id']}'),
              Text('Job：${summary['job_id']}'),
              Text('Job 状态：${summary['job_status']}'),
              Text('Material 状态：${summary['material_status']}'),
              Text('图片记录：${summary['image_record_count']}'),
              Text('学习资产：${summary['learning_asset_count']}'),
              Text('复习任务：${summary['review_task_count']}'),
              Text('报告资产：${summary['report_asset_count']}'),
            ],
            const SizedBox(height: 20),
            const Text('执行日志'),
            const SizedBox(height: 8),
            for (final item in _logs) Text(item),
          ],
        ),
      ),
    );
  }

  Future<void> _run() async {
    final imageUrls = _sourceImageUrlsValue
        .split(',')
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
    if (imageUrls.isEmpty) {
      _emitHarnessResult({
        'status': 'failed',
        'error': '缺少 SOURCE_IMAGE_URLS',
      });
      setState(() {
        _error = '缺少 SOURCE_IMAGE_URLS';
        _running = false;
      });
      return;
    }

    final dio = Dio(BaseOptions(baseUrl: _apiBaseUrl));
    try {
      _log('API: $_apiBaseUrl');
      await dio.getUri(Uri.parse(_apiBaseUrl).replace(path: '/healthz'));
      final token = await _login(dio);
      final options = Options(headers: {'Authorization': 'Bearer $token'});
      final childId = await _createChild(dio, options);
      final images = await _downloadImages(dio, imageUrls);
      final upload = await _createMaterial(dio, options, childId, images);
      final materialId = upload.materialId;
      final jobId = upload.jobId;
      final parsedJob = await _pollJob(dio, options, jobId);
      if (parsedJob['status'] != 'needs_review') {
        throw StateError('AI 校对未进入 needs_review：${parsedJob['status']}');
      }
      await _confirmJob(dio, options, parsedJob);
      final material = await _getMaterial(dio, options, materialId);
      final knowledgePack = await _getKnowledgePack(dio, options, materialId);
      final reviewTasks = await _getReviewTasks(
        dio,
        options,
        childId: childId,
        materialId: materialId,
      );
      final report = await _getWeeklyReport(dio, options, childId);
      final summary = <String, dynamic>{
        'status': 'passed',
        'title': upload.title,
        'material_id': materialId,
        'job_id': jobId,
        'job_status': parsedJob['status'],
        'material_status': material['status'],
        'image_record_count': _listLength(material['image_records']),
        'learning_asset_count': _listLength(material['learning_assets']),
        'knowledge_pack_topic': knowledgePack['topic'],
        'review_task_count': _listLength(reviewTasks['items']),
        'report_asset_count': _listLength(report['asset_mastery']),
      };
      _emitHarnessResult(summary);
      setState(() {
        _summary = summary;
        _running = false;
      });
      _log('完成：$materialId');
    } catch (error) {
      _emitHarnessResult({
        'status': 'failed',
        'error': '${error.runtimeType}: $error',
      });
      setState(() {
        _error = '${error.runtimeType}: $error';
        _running = false;
      });
    }
  }

  Future<String> _login(Dio dio) async {
    final authCode =
        'hn019-real-device-${DateTime.now().millisecondsSinceEpoch}';
    final login = await dio.post<Map<String, dynamic>>(
      '/auth/wechat/login',
      data: {'auth_code': authCode},
    );
    final loginPayload = login.data ?? const <String, dynamic>{};
    final bindToken = loginPayload['bind_token'] as String?;
    if ((loginPayload['status'] as String?) == 'authenticated') {
      _log('登录：已认证');
      return ((loginPayload['tokens'] as Map<String, dynamic>)['access_token'])
          as String;
    }
    final phoneNumber = '13900001919';
    final otp = await dio.post<Map<String, dynamic>>(
      '/auth/phone/request-otp',
      data: {'bind_token': bindToken, 'phone_number': phoneNumber},
    );
    final code = (otp.data?['debug_code'] as String?) ?? '123456';
    final bound = await dio.post<Map<String, dynamic>>(
      '/auth/phone/bind',
      data: {
        'bind_token': bindToken,
        'phone_number': phoneNumber,
        'otp_code': code,
      },
    );
    _log('登录：手机绑定完成');
    return ((bound.data?['tokens'] as Map<String, dynamic>)['access_token'])
        as String;
  }

  Future<String> _createChild(Dio dio, Options options) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/children',
      options: options,
      data: {
        'name': 'Mia HN019',
        'age': 6,
        'level': 'starter',
        'learning_goal': '真机主链验证',
        'preferred_review_duration_minutes': 10,
        'parent_notes': 'HN-019 real device main chain harness',
      },
    );
    final id = response.data?['id'] as String;
    _log('孩子档案：$id');
    return id;
  }

  Future<List<_SourceImage>> _downloadImages(Dio dio, List<String> urls) async {
    final tempDir = await getTemporaryDirectory();
    final images = <_SourceImage>[];
    for (var index = 0; index < urls.length; index += 1) {
      final uri = Uri.parse(urls[index]);
      final response = await dio.get<List<int>>(
        uri.toString(),
        options: Options(responseType: ResponseType.bytes),
      );
      final contentType = _imageContentTypeFor(
        uri,
        response.headers.value(Headers.contentTypeHeader),
      );
      final extension = _extensionForContentType(contentType);
      final filename = 'hn019-page-${index + 1}.$extension';
      final path = '${tempDir.path}/$filename';
      await File(path).writeAsBytes(response.data ?? const <int>[]);
      images.add(
        _SourceImage(
          path: path,
          filename: filename,
          contentType: contentType,
        ),
      );
      _log('讲义图片下载：第 ${index + 1} 页');
    }
    return images;
  }

  Future<_UploadResult> _createMaterial(
    Dio dio,
    Options options,
    String childId,
    List<_SourceImage> images,
  ) async {
    final title =
        'HN-019 Device Main Chain ${DateTime.now().millisecondsSinceEpoch}';
    final files = <MultipartFile>[];
    for (final image in images) {
      files.add(
        await MultipartFile.fromFile(
          image.path,
          filename: image.filename,
          contentType: _mediaTypeForContentType(image.contentType),
        ),
      );
    }
    final form = FormData.fromMap({
      'child_id': childId,
      'teacher_name': 'Harness',
      'lesson_date': '2026-06-02',
      'title': title,
      'topic': '真机讲义主链',
      'tags': 'harness,hn019',
      'file_sources': List<String>.filled(files.length, 'gallery'),
      'files': files,
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/materials',
      options: options,
      data: form,
    );
    final payload = response.data ?? const <String, dynamic>{};
    final material = payload['material'] as Map<String, dynamic>;
    final job = payload['job'] as Map<String, dynamic>;
    _log('讲义：${material['id']}');
    return _UploadResult(
      title: title,
      materialId: material['id'] as String,
      jobId: job['id'] as String,
    );
  }

  Future<Map<String, dynamic>> _pollJob(
    Dio dio,
    Options options,
    String jobId,
  ) async {
    for (var i = 0; i < 100; i += 1) {
      await Future<void>.delayed(const Duration(seconds: 3));
      final response = await dio.get<Map<String, dynamic>>(
        '/material-jobs/$jobId',
        options: options,
      );
      final job = response.data ?? const <String, dynamic>{};
      _log('AI 校对：${job['status']}');
      if (job['status'] == 'needs_review' ||
          job['status'] == 'ready' ||
          job['status'] == 'failed') {
        return job;
      }
    }
    throw TimeoutException('等待 AI 校对超时');
  }

  Future<void> _confirmJob(
    Dio dio,
    Options options,
    Map<String, dynamic> job,
  ) async {
    await dio.post<Map<String, dynamic>>(
      '/material-jobs/${job['id']}/confirm',
      options: options,
      data: {
        'draft_title': job['draft_title'],
        'draft_topic': job['draft_topic'],
        'draft_vocabulary': job['draft_vocabulary'],
        'draft_sentences': job['draft_sentences'],
      },
    );
    _log('AI 校对：已确认');
  }

  Future<Map<String, dynamic>> _getMaterial(
    Dio dio,
    Options options,
    String materialId,
  ) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/materials/$materialId',
      options: options,
    );
    return (response.data?['material'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> _getKnowledgePack(
    Dio dio,
    Options options,
    String materialId,
  ) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/knowledge-packs/$materialId',
      options: options,
    );
    return (response.data?['knowledge_pack'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> _getReviewTasks(
    Dio dio,
    Options options, {
    required String childId,
    required String materialId,
  }) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/review-tasks',
      queryParameters: {'child_id': childId, 'material_id': materialId},
      options: options,
    );
    return response.data ?? const <String, dynamic>{};
  }

  Future<Map<String, dynamic>> _getWeeklyReport(
    Dio dio,
    Options options,
    String childId,
  ) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/reports/weekly',
      queryParameters: {'child_id': childId},
      options: options,
    );
    return (response.data?['report'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
  }

  int _listLength(Object? value) => value is List ? value.length : 0;

  void _log(String message) {
    setState(() => _logs.insert(0, message));
  }

  void _emitHarnessResult(Map<String, dynamic> payload) {
    // ignore: avoid_print
    print('HN019_RESULT:${jsonEncode(payload)}');
  }
}

class _SourceImage {
  const _SourceImage({
    required this.path,
    required this.filename,
    required this.contentType,
  });

  final String path;
  final String filename;
  final String contentType;
}

String _imageContentTypeFor(Uri uri, String? headerValue) {
  final normalized = headerValue?.split(';').first.trim().toLowerCase();
  if (_isSupportedImageContentType(normalized)) {
    return normalized!;
  }
  final path = uri.path.toLowerCase();
  if (path.endsWith('.png')) {
    return 'image/png';
  }
  if (path.endsWith('.webp')) {
    return 'image/webp';
  }
  if (path.endsWith('.heic')) {
    return 'image/heic';
  }
  if (path.endsWith('.heif')) {
    return 'image/heif';
  }
  return 'image/jpeg';
}

bool _isSupportedImageContentType(String? value) {
  return value == 'image/jpeg' ||
      value == 'image/jpg' ||
      value == 'image/png' ||
      value == 'image/webp' ||
      value == 'image/heic' ||
      value == 'image/heif';
}

String _extensionForContentType(String contentType) {
  switch (contentType) {
    case 'image/png':
      return 'png';
    case 'image/webp':
      return 'webp';
    case 'image/heic':
      return 'heic';
    case 'image/heif':
      return 'heif';
    default:
      return 'jpg';
  }
}

DioMediaType _mediaTypeForContentType(String contentType) {
  final parts = contentType.split('/');
  if (parts.length != 2 || parts.first.isEmpty || parts.last.isEmpty) {
    return DioMediaType('image', 'jpeg');
  }
  final subtype = parts.last == 'jpg' ? 'jpeg' : parts.last;
  return DioMediaType(parts.first, subtype);
}

class _UploadResult {
  const _UploadResult({
    required this.title,
    required this.materialId,
    required this.jobId,
  });

  final String title;
  final String materialId;
  final String jobId;
}
