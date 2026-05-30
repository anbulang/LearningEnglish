import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:path_provider/path_provider.dart';

import 'package:learning_english_mobile/core/theme/app_theme.dart';

const _apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000/v1',
);
const _sampleAudioUrl =
    'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav';

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
  SpeakingAttempt? _attempt;
  String? _error;
  bool _running = true;

  @override
  void initState() {
    super.initState();
    unawaited(_run());
  }

  @override
  Widget build(BuildContext context) {
    final attempt = _attempt;
    return Scaffold(
      appBar: AppBar(title: const Text('HN-017 真机口语验证')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: <Widget>[
            Text(_running ? '正在执行真机上传闭环...' : '真机上传闭环完成',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 16),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: Colors.red)),
            if (attempt != null) ...<Widget>[
              Text('状态：${attempt.status.name}'),
              Text('Attempt：${attempt.id}'),
              Text('转写：${attempt.transcript}'),
              Text('总分：${attempt.overallScore?.round() ?? 0}'),
              Text(
                '发音：${((attempt.pronunciationScore ?? 0) * 100).round()} · '
                '准确：${attempt.accuracyScore?.round() ?? 0} · '
                '流利：${attempt.fluencyScore?.round() ?? 0} · '
                '完整：${attempt.completenessScore?.round() ?? 0}',
              ),
              Text('反馈：${attempt.feedback}'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final item in attempt.wordFeedback)
                    Chip(label: Text('${item.word} ${item.score?.round() ?? 0}')),
                ],
              ),
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
    final dio = Dio(BaseOptions(baseUrl: _apiBaseUrl));
    try {
      _log('API: $_apiBaseUrl');
      await dio.getUri(Uri.parse(_apiBaseUrl).replace(path: '/healthz'));
      final token = await _login(dio);
      final options = Options(headers: {'Authorization': 'Bearer $token'});
      final childId = await _createChild(dio, options);
      final materialId = await _createMaterial(dio, options, childId);
      final audioPath = await _downloadSampleAudio(dio);
      final created = await _uploadSpeakingAttempt(
        dio,
        options,
        childId: childId,
        materialId: materialId,
        audioPath: audioPath,
      );
      _setAttempt(created);
      final scored = await _pollAttempt(dio, options, created.id);
      _setAttempt(scored);
      _log('完成：${scored.status.name}');
    } catch (error) {
      setState(() {
        _error = '${error.runtimeType}: $error';
        _running = false;
      });
    }
  }

  Future<String> _login(Dio dio) async {
    final authCode = 'hn017-real-device-${DateTime.now().millisecondsSinceEpoch}';
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
    final phoneNumber = '13900001717';
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
        'name': 'Mia',
        'age': 6,
        'level': 'starter',
        'learning_goal': '真机口语验证',
        'preferred_review_duration_minutes': 10,
        'parent_notes': 'HN-017 real device harness',
      },
    );
    final id = response.data?['id'] as String;
    _log('孩子档案：$id');
    return id;
  }

  Future<String> _createMaterial(
    Dio dio,
    Options options,
    String childId,
  ) async {
    final tempDir = await getTemporaryDirectory();
    final imagePath = '${tempDir.path}/hn017-minimal.png';
    await File(imagePath).writeAsBytes(base64Decode(_onePixelPngBase64));
    final form = FormData.fromMap({
      'child_id': childId,
      'teacher_name': 'Harness',
      'lesson_date': '2026-05-27',
      'title': 'HN-017 Speaking',
      'topic': 'Hello world',
      'tags': 'speaking',
      'file_sources': ['gallery'],
      'files': [
        await MultipartFile.fromFile(
          imagePath,
          filename: 'hn017-minimal.png',
          contentType: DioMediaType('image', 'png'),
        ),
      ],
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/materials',
      options: options,
      data: form,
    );
    final material =
        response.data?['material'] as Map<String, dynamic>? ?? const {};
    final id = material['id'] as String;
    _log('讲义：$id');
    return id;
  }

  Future<String> _downloadSampleAudio(Dio dio) async {
    final tempDir = await getTemporaryDirectory();
    final path = '${tempDir.path}/hello-world.wav';
    await dio.download(_sampleAudioUrl, path);
    _log('音频下载完成');
    return path;
  }

  Future<SpeakingAttempt> _uploadSpeakingAttempt(
    Dio dio,
    Options options, {
    required String childId,
    required String materialId,
    required String audioPath,
  }) async {
    final form = FormData.fromMap({
      'child_id': childId,
      'material_id': materialId,
      'prompt_text': '跟读：Hello world.',
      'target_text': 'Hello world.',
      'learning_asset_id': 'asset_hello',
      'audio_duration_ms': 1800,
      'audio': await MultipartFile.fromFile(
        audioPath,
        filename: 'hello-world.wav',
        contentType: DioMediaType('audio', 'wav'),
      ),
    });
    final response = await dio.post<Map<String, dynamic>>(
      '/speaking-attempts',
      options: options,
      data: form,
    );
    final attempt = SpeakingAttempt.fromJson(response.data ?? {});
    _log('已上传：${attempt.id}');
    return attempt;
  }

  Future<SpeakingAttempt> _pollAttempt(
    Dio dio,
    Options options,
    String attemptId,
  ) async {
    for (var i = 0; i < 80; i += 1) {
      await Future<void>.delayed(const Duration(seconds: 3));
      final response = await dio.get<Map<String, dynamic>>(
        '/speaking-attempts/$attemptId',
        options: options,
      );
      final attempt = SpeakingAttempt.fromJson(response.data ?? {});
      _setAttempt(attempt);
      _log('轮询：${attempt.status.name}');
      if (attempt.status == SpeakingAttemptStatus.scored ||
          attempt.status == SpeakingAttemptStatus.failed) {
        setState(() => _running = false);
        return attempt;
      }
    }
    throw TimeoutException('等待口语评分超时');
  }

  void _setAttempt(SpeakingAttempt attempt) {
    setState(() => _attempt = attempt);
  }

  void _log(String message) {
    setState(() => _logs.insert(0, message));
  }
}

const _onePixelPngBase64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/l2n2VwAAAABJRU5ErkJggg==';
