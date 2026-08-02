import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

import '../../../helpers/fake_dio_adapter.dart';

void main() {
  group('AppRepository authorization recovery', () {
    test('refreshes token and retries once after a 401 response', () async {
      var currentToken = 'expired-token';
      var refreshCalls = 0;
      final seenAuthorizationHeaders = <String?>[];

      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://localhost/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (options) {
            seenAuthorizationHeaders
                .add(options.headers['Authorization'] as String?);
            return ResponseBody.fromString(
              jsonEncode(<String, dynamic>{'detail': 'Invalid access token'}),
              401,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
          (options) {
            seenAuthorizationHeaders
                .add(options.headers['Authorization'] as String?);
            return ResponseBody.fromString(
              jsonEncode([
                <String, dynamic>{
                  'id': 'material_1',
                  'child_id': 'child_1',
                  'teacher_name': 'Emma',
                  'lesson_date': '2026-04-27T00:00:00.000',
                  'title': 'Animals Around Me',
                  'topic': '动物',
                  'status': 'ready',
                  'source_images': <String>[],
                  'pdf_url': '',
                  'ocr_text': 'cat dog bird',
                  'tags': <String>['动物'],
                },
              ]),
              200,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => currentToken,
        refreshSession: () async {
          refreshCalls += 1;
          currentToken = 'fresh-token';
          return true;
        },
      );

      final materials = await repository.listMaterials(childId: 'child_1');

      expect(materials, hasLength(1));
      expect(materials.first.id, 'material_1');
      expect(refreshCalls, 1);
      expect(
        seenAuthorizationHeaders,
        <String?>['Bearer expired-token', 'Bearer fresh-token'],
      );
    });

    test('rethrows unauthorized error when refresh fails', () async {
      var refreshCalls = 0;
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://localhost/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode(<String, dynamic>{'detail': 'Invalid access token'}),
                401,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'expired-token',
        refreshSession: () async {
          refreshCalls += 1;
          return false;
        },
      );

      await expectLater(
        repository.listMaterials(childId: 'child_1'),
        throwsA(
          isA<DioException>().having(
            (error) => error.response?.statusCode,
            'statusCode',
            401,
          ),
        ),
      );
      expect(refreshCalls, 1);
    });

    test('rewrites internal MinIO image URLs to the API upload host', () async {
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode([
                  <String, dynamic>{
                    'id': 'material_1',
                    'child_id': 'child_1',
                    'teacher_name': 'Emma',
                    'lesson_date': '2026-05-11T00:00:00.000',
                    'title': 'Storybook',
                    'topic': 'phonics',
                    'status': 'ready',
                    'source_images': <String>[
                      'http://minio:9000/learning-english/material/material_1/page.jpg',
                    ],
                    'pdf_url': '',
                    'ocr_text': '',
                    'tags': <String>['phonics'],
                    'image_records': <Map<String, dynamic>>[
                      <String, dynamic>{
                        'id': 'image_1',
                        'page_index': 1,
                        'source_type': 'gallery',
                        'original_filename': 'page.jpg',
                        'url':
                            'http://minio:9000/learning-english/material/material_1/page.jpg',
                        'object_key': 'material/material_1/page.jpg',
                        'content_type': 'image/jpeg',
                        'size_bytes': 100,
                        'image_title': 'Qq Storybook',
                        'ocr_text': '',
                        'vocabulary': <String>['queen'],
                        'sentences': <String>['Find the queen.'],
                        'details': <String>['AI 已完成图片级识别，请家长确认。'],
                      },
                    ],
                  },
                ]),
                200,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final materials = await repository.listMaterials(childId: 'child_1');

      expect(
        materials.single.sourceImages.single,
        'http://127.0.0.1:8000/uploads/material/material_1/page.jpg',
      );
      expect(
        materials.single.imageRecords.single.url,
        'http://127.0.0.1:8000/uploads/material/material_1/page.jpg',
      );
    });

    test('parses learning assets and rewrites media URLs', () async {
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode(<String, dynamic>{
                  'material': <String, dynamic>{
                    'id': 'material_1',
                    'child_id': 'child_1',
                    'teacher_name': '外教课',
                    'lesson_date': '2026-05-12',
                    'title': 'Qq Rr Storybook',
                    'topic': 'phonics',
                    'status': 'ready',
                    'source_images': <String>[],
                    'pdf_url': '',
                    'ocr_text': '',
                    'tags': <String>[],
                    'image_records': <Map<String, dynamic>>[],
                    'learning_assets': <Map<String, dynamic>>[
                      <String, dynamic>{
                        'id': 'asset_queen',
                        'text': 'queen',
                        'kind': 'word',
                        'translation': '女王',
                        'source_page_index': 1,
                        'source_bbox': <String, dynamic>{
                          'x': 0.05,
                          'y': 0.14,
                          'width': 0.43,
                          'height': 0.35,
                        },
                        'source_visual_description': '迷宫里的女王。',
                        'pronunciation_text': 'queen',
                        'image_prompt': '参考讲义生成彩色图。',
                        'difficulty': 'easy',
                        'teaching_note': '读 queen。',
                        'is_core': true,
                        'generated_image_status': 'ready',
                        'generated_image_url':
                            'http://localhost:8000/mock-media/hn014/images/queen.svg',
                        'generated_image_object_key':
                            'mock_media/hn014/images/queen.svg',
                        'tts_us_status': 'ready',
                        'tts_us_url':
                            'http://minio:9000/learning-english/mock-media/hn014/tts/us/queen.m4a',
                        'tts_us_object_key':
                            'mock_media/hn014/tts/us/queen.m4a',
                        'tts_uk_status': 'ready',
                        'tts_uk_url':
                            'http://minio:9000/learning-english/mock-media/hn014/tts/uk/queen.m4a',
                        'tts_uk_object_key':
                            'mock_media/hn014/tts/uk/queen.m4a',
                        'primary_accent': 'us',
                      },
                    ],
                  },
                }),
                200,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final material = await repository.getMaterial('material_1');
      final asset = material.learningAssets.single;

      expect(asset.text, 'queen');
      expect(asset.translation, '女王');
      expect(asset.sourceBbox?.x, 0.05);
      expect(
        asset.generatedImageUrl,
        'http://127.0.0.1:8000/mock-media/hn014/images/queen.svg',
      );
      expect(
        asset.ttsUsUrl,
        'http://127.0.0.1:8000/uploads/mock-media/hn014/tts/us/queen.m4a',
      );
      expect(
        asset.ttsUkUrl,
        'http://127.0.0.1:8000/uploads/mock-media/hn014/tts/uk/queen.m4a',
      );
    });

    test('parses learning asset media error fields', () {
      final asset = LearningAsset.fromJson(<String, dynamic>{
        'id': 'asset_queen',
        'text': 'queen',
        'kind': 'word',
        'generated_image_status': 'failed',
        'generated_image_error': '图片生成失败：provider timeout',
        'tts_us_status': 'failed',
        'tts_us_error': '美式发音生成失败：provider timeout',
        'tts_uk_status': 'failed',
        'tts_uk_error': '英式发音生成失败：provider timeout',
      });

      expect(asset.generatedImageError, '图片生成失败：provider timeout');
      expect(asset.ttsUsError, '美式发音生成失败：provider timeout');
      expect(asset.ttsUkError, '英式发音生成失败：provider timeout');
    });

    test('keeps non-runtime localhost media URLs unchanged', () async {
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode(<String, dynamic>{
                  'material': <String, dynamic>{
                    'id': 'material_1',
                    'child_id': 'child_1',
                    'teacher_name': '外教课',
                    'lesson_date': '2026-05-12',
                    'title': 'Qq Rr Storybook',
                    'topic': 'phonics',
                    'status': 'ready',
                    'source_images': <String>[],
                    'pdf_url': '',
                    'ocr_text': '',
                    'tags': <String>[],
                    'image_records': <Map<String, dynamic>>[],
                    'learning_assets': <Map<String, dynamic>>[
                      <String, dynamic>{
                        'id': 'asset_external',
                        'text': 'external',
                        'kind': 'word',
                        'generated_image_url':
                            'http://localhost:9999/external/asset.svg',
                      },
                    ],
                  },
                }),
                200,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final material = await repository.getMaterial('material_1');

      expect(
        material.learningAssets.single.generatedImageUrl,
        'http://localhost:9999/external/asset.svg',
      );
    });

    test('parses draft learning assets from material jobs', () async {
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode(<String, dynamic>{
                  'id': 'job_1',
                  'material_id': 'material_1',
                  'status': 'needs_review',
                  'confidence_summary': '识别完成',
                  'warnings': <String>[],
                  'started_at': '2026-05-12T10:00:00Z',
                  'finished_at': null,
                  'draft_title': 'Qq Rr Storybook',
                  'draft_topic': 'phonics',
                  'draft_vocabulary': <String>['queen'],
                  'draft_sentences': <String>['Find the queen.'],
                  'draft_image_records': <Map<String, dynamic>>[],
                  'draft_learning_assets': <Map<String, dynamic>>[
                    <String, dynamic>{
                      'id': 'asset_rabbit',
                      'text': 'rabbit',
                      'kind': 'word',
                      'translation': '兔子',
                      'source_page_index': 2,
                      'generated_image_status': 'pending',
                      'tts_us_status': 'pending',
                      'tts_uk_status': 'pending',
                      'primary_accent': 'uk',
                    },
                  ],
                }),
                200,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final job = await repository.getMaterialJob('job_1');

      expect(job.draftLearningAssets.single.text, 'rabbit');
      expect(job.draftLearningAssets.single.sourcePageIndex, 2);
      expect(job.draftLearningAssets.single.primaryAccent, 'uk');
    });

    test('patches learning asset primary accent and returns material',
        () async {
      final seenBodies = <Map<String, dynamic>>[];
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (options) {
            seenBodies.add(
              Map<String, dynamic>.from(options.data as Map),
            );
            return ResponseBody.fromString(
              jsonEncode(<String, dynamic>{
                'material': <String, dynamic>{
                  'id': 'material_1',
                  'child_id': 'child_1',
                  'teacher_name': '外教课',
                  'lesson_date': '2026-05-12',
                  'title': 'Qq Rr Storybook',
                  'topic': 'phonics',
                  'status': 'ready',
                  'source_images': <String>[],
                  'pdf_url': '',
                  'ocr_text': '',
                  'tags': <String>[],
                  'image_records': <Map<String, dynamic>>[],
                  'learning_assets': <Map<String, dynamic>>[
                    <String, dynamic>{
                      'id': 'asset_queen',
                      'text': 'queen',
                      'kind': 'word',
                      'translation': '女王',
                      'primary_accent': 'uk',
                    },
                  ],
                },
              }),
              200,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final material = await repository.updateLearningAssetPrimaryAccent(
        materialId: 'material_1',
        assetId: 'asset_queen',
        primaryAccent: 'uk',
      );

      expect(seenBodies.single, <String, dynamic>{'primary_accent': 'uk'});
      expect(material.learningAssets.single.primaryAccent, 'uk');
    });

    test('uploads speaking attempt as multipart audio', () async {
      final tempDir = await Directory.systemTemp.createTemp('speaking-audio-');
      final audioFile = File('${tempDir.path}/rabbit.m4a');
      await audioFile.writeAsBytes(<int>[1, 2, 3, 4]);
      addTearDown(() async {
        if (await tempDir.exists()) {
          await tempDir.delete(recursive: true);
        }
      });
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (request) {
            expect(request.path, '/speaking-attempts');
            expect(request.data, isA<FormData>());
            return ResponseBody.fromString(
              jsonEncode(<String, dynamic>{
                'id': 'attempt_test',
                'child_id': 'child_test',
                'material_id': 'material_test',
                'review_task_id': 'task_test',
                'learning_asset_id': 'asset_rabbit',
                'prompt_text': '跟读：A rabbit can hop fast.',
                'target_text': 'A rabbit can hop fast.',
                'audio_url':
                    'http://testserver/uploads/speaking_attempt/attempt_test/input.m4a',
                'audio_object_key': 'speaking_attempt/attempt_test/input.m4a',
                'audio_content_type': 'audio/mp4',
                'audio_size_bytes': 10,
                'audio_duration_ms': 3100,
                'transcript': '',
                'pronunciation_score': null,
                'overall_score': null,
                'accuracy_score': null,
                'fluency_score': null,
                'completeness_score': null,
                'feedback': '',
                'word_feedback': <Map<String, dynamic>>[],
                'suggestions': <String>[],
                'provider': '',
                'raw_result': <String, dynamic>{},
                'failure_reason': '',
                'status': 'recording_uploaded',
              }),
              201,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final attempt = await repository.uploadSpeakingAttempt(
        childId: 'child_test',
        materialId: 'material_test',
        reviewTaskId: 'task_test',
        learningAssetId: 'asset_rabbit',
        promptText: '跟读：A rabbit can hop fast.',
        targetText: 'A rabbit can hop fast.',
        audioPath: audioFile.path,
        audioDurationMs: 3100,
      );

      expect(attempt.status, SpeakingAttemptStatus.recordingUploaded);
      expect(attempt.audioObjectKey, 'speaking_attempt/attempt_test/input.m4a');
      expect(attempt.audioDurationMs, 3100);
    });

    test('rebuilds speaking multipart body before authorization retry',
        () async {
      final tempDir = await Directory.systemTemp.createTemp('speaking-audio-');
      final audioFile = File('${tempDir.path}/rabbit.m4a');
      await audioFile.writeAsBytes(<int>[1, 2, 3, 4]);
      addTearDown(() async {
        if (await tempDir.exists()) {
          await tempDir.delete(recursive: true);
        }
      });
      var currentToken = 'expired-token';
      var refreshCalls = 0;
      final forms = <FormData>[];
      final dio = Dio(
        BaseOptions(
          baseUrl: 'http://127.0.0.1:8000/v1',
        ),
      )..httpClientAdapter = SequenceDioAdapter([
          (request) {
            expect(request.path, '/speaking-attempts');
            forms.add(request.data as FormData);
            return ResponseBody.fromString(
              jsonEncode(<String, dynamic>{'detail': 'Invalid access token'}),
              401,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
          (request) {
            expect(request.path, '/speaking-attempts');
            forms.add(request.data as FormData);
            return ResponseBody.fromString(
              jsonEncode(<String, dynamic>{
                'id': 'attempt_test',
                'child_id': 'child_test',
                'material_id': 'material_test',
                'review_task_id': '',
                'learning_asset_id': 'asset_rabbit',
                'prompt_text': '跟读：A rabbit can hop fast.',
                'target_text': 'A rabbit can hop fast.',
                'audio_url':
                    'http://testserver/uploads/speaking_attempt/attempt_test/input.m4a',
                'audio_object_key': 'speaking_attempt/attempt_test/input.m4a',
                'audio_content_type': 'audio/mp4',
                'audio_size_bytes': 10,
                'audio_duration_ms': 3100,
                'transcript': '',
                'pronunciation_score': null,
                'overall_score': null,
                'accuracy_score': null,
                'fluency_score': null,
                'completeness_score': null,
                'feedback': '',
                'word_feedback': <Map<String, dynamic>>[],
                'suggestions': <String>[],
                'provider': '',
                'raw_result': <String, dynamic>{},
                'failure_reason': '',
                'status': 'recording_uploaded',
              }),
              201,
              headers: <String, List<String>>{
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
          },
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => currentToken,
        refreshSession: () async {
          refreshCalls += 1;
          currentToken = 'fresh-token';
          return true;
        },
      );

      final attempt = await repository.uploadSpeakingAttempt(
        childId: 'child_test',
        materialId: 'material_test',
        learningAssetId: 'asset_rabbit',
        promptText: '跟读：A rabbit can hop fast.',
        targetText: 'A rabbit can hop fast.',
        audioPath: audioFile.path,
        audioDurationMs: 3100,
      );

      expect(attempt.status, SpeakingAttemptStatus.recordingUploaded);
      expect(refreshCalls, 1);
      expect(forms, hasLength(2));
      expect(identical(forms[0], forms[1]), isFalse);
    });
  });

  group('AppRepository weekly trends', () {
    test('parses ordered weekly trend points', () async {
      final dio = Dio(
        BaseOptions(baseUrl: 'http://127.0.0.1:8000/v1'),
      )..httpClientAdapter = SequenceDioAdapter([
          (_) => ResponseBody.fromString(
                jsonEncode(<String, dynamic>{
                  'child_id': 'child_1',
                  'points': <Map<String, dynamic>>[
                    <String, dynamic>{
                      'week_start': '2026-07-06',
                      'week_end': '2026-07-12',
                      'completed_sessions': 1,
                      'reviewed_words': 4,
                      'speaking_attempts': 0,
                      'weak_item_count': 2,
                    },
                    <String, dynamic>{
                      'week_start': '2026-07-13',
                      'week_end': '2026-07-19',
                      'completed_sessions': 3,
                      'reviewed_words': 6,
                      'speaking_attempts': 2,
                      'weak_item_count': 1,
                    },
                  ],
                }),
                200,
                headers: <String, List<String>>{
                  Headers.contentTypeHeader: <String>['application/json'],
                },
              ),
        ]);

      final repository = AppRepository(
        dio,
        accessToken: () => 'token',
        refreshSession: () async => false,
      );

      final trends =
          await repository.getWeeklyTrends(childId: 'child_1', weeks: 8);

      expect(trends.childId, 'child_1');
      expect(trends.points, hasLength(2));
      expect(trends.points.first.completedSessions, 1);
      expect(trends.points.last.completedSessions, 3);
      expect(trends.points.last.weakItemCount, 1);
      expect(trends.points.first.weekStart, DateTime(2026, 7, 6));
    });
  });
}
