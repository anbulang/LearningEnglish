import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

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
      )..httpClientAdapter = _SequenceAdapter([
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
      )..httpClientAdapter = _SequenceAdapter([
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
  });
}

class _SequenceAdapter implements HttpClientAdapter {
  _SequenceAdapter(this._handlers);

  final List<ResponseBody Function(RequestOptions options)> _handlers;
  var _index = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (_index >= _handlers.length) {
      throw StateError('No response configured for request #$_index');
    }
    final handler = _handlers[_index];
    _index += 1;
    return handler(options);
  }
}
