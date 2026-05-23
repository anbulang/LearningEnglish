import 'dart:convert';

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
  });
}
