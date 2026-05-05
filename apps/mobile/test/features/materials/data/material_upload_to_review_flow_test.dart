import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/data/scan_draft_controller.dart';

import '../../../helpers/fake_dio_adapter.dart';

void main() {
  group('material upload to AI review flow', () {
    test('uploads a worksheet and reads the generated review job', () async {
      final tempDir =
          await Directory.systemTemp.createTemp('learning_english_upload_');
      addTearDown(() => tempDir.delete(recursive: true));
      final worksheet = File('${tempDir.path}/worksheet.jpg');
      await worksheet.writeAsBytes(<int>[0xff, 0xd8, 0xff, 0xd9]);

      final requests = <RequestOptions>[];
      final adapter = SequenceDioAdapter([
        (options) {
          requests.add(options);
          expect(options.method, 'POST');
          expect(options.path, '/materials');
          expect(
            options.headers['Authorization'],
            'Bearer access-token',
          );
          expect(
            options.contentType,
            startsWith(Headers.multipartFormDataContentType),
          );
          final formData = options.data as FormData;
          expect(
            formData.fields
                .where((field) => field.key == 'file_sources')
                .map((field) => field.value),
            <String>['camera'],
          );

          return _jsonResponse(<String, dynamic>{
            'material': _materialJson(status: 'processing'),
            'job': _jobJson(status: 'needs_review'),
          });
        },
        (options) {
          requests.add(options);
          expect(options.method, 'GET');
          expect(options.path, '/material-jobs/job_1');
          expect(
            options.headers['Authorization'],
            'Bearer access-token',
          );

          return _jsonResponse(_jobJson(status: 'needs_review'));
        },
      ]);

      final dio = Dio(BaseOptions(baseUrl: 'http://localhost/v1'))
        ..httpClientAdapter = adapter;
      final repository = AppRepository(
        dio,
        accessToken: () => 'access-token',
        refreshSession: () async => false,
      );

      final created = await repository.uploadMaterial(
        childId: 'child_1',
        teacherName: 'Emma',
        lessonDate: DateTime(2026, 4, 27),
        title: 'Animals Around Me',
        topic: '动物',
        files: <ScanDraftPage>[
          ScanDraftPage(
            sourceType: 'camera',
            file: XFile(
              worksheet.path,
              name: 'worksheet.jpg',
              mimeType: 'image/jpeg',
            ),
          ),
        ],
      );
      final reviewJob = await repository.getMaterialJob(created.job.id);

      expect(created.material.id, 'material_1');
      expect(created.material.status, MaterialStatus.processing);
      expect(created.material.imageRecords, isEmpty);
      expect(created.job.status, JobStatus.needsReview);
      expect(reviewJob.status, JobStatus.needsReview);
      expect(reviewJob.draftTitle, 'Animals Around Me');
      expect(reviewJob.draftVocabulary, <String>['cat', 'dog', 'bird']);
      expect(
        requests.map((request) => request.path),
        <String>['/materials', '/material-jobs/job_1'],
      );
    });
  });
}

ResponseBody _jsonResponse(Object payload, {int statusCode = 200}) {
  return ResponseBody.fromString(
    jsonEncode(payload),
    statusCode,
    headers: <String, List<String>>{
      Headers.contentTypeHeader: <String>['application/json'],
    },
  );
}

Map<String, dynamic> _materialJson({required String status}) {
  return <String, dynamic>{
    'id': 'material_1',
    'child_id': 'child_1',
    'teacher_name': 'Emma',
    'lesson_date': '2026-04-27T00:00:00.000',
    'title': 'Animals Around Me',
    'topic': '动物',
    'status': status,
    'source_images': <String>['materials/material_1/source/worksheet.jpg'],
    'pdf_url': '',
    'ocr_text': 'cat dog bird',
    'tags': <String>['动物'],
  };
}

Map<String, dynamic> _jobJson({required String status}) {
  return <String, dynamic>{
    'id': 'job_1',
    'material_id': 'material_1',
    'status': status,
    'confidence_summary': '识别结果可信，建议家长确认核心词汇。',
    'warnings': <String>[],
    'started_at': '2026-04-27T10:00:00.000',
    'finished_at': null,
    'draft_title': 'Animals Around Me',
    'draft_topic': '动物',
    'draft_vocabulary': <String>['cat', 'dog', 'bird'],
    'draft_sentences': <String>['It is a cat.', 'I can see a dog.'],
  };
}
