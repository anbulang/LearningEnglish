import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_navigation.dart';

void main() {
  test('ready material opens lesson detail', () {
    expect(
      materialDestination(_material(status: MaterialStatus.ready)),
      '/lessons/material_1',
    );
  });

  test('non-ready material with parse job opens AI review', () {
    for (final status in <MaterialStatus>[
      MaterialStatus.uploaded,
      MaterialStatus.processing,
      MaterialStatus.needsReview,
      MaterialStatus.failed,
    ]) {
      expect(
        materialDestination(_material(status: status)),
        '/materials/review/job_1?materialId=material_1',
      );
    }
  });

  test('non-ready material without parse job stays in materials library', () {
    expect(
      materialDestination(
        _material(status: MaterialStatus.processing, parseJobId: ''),
      ),
      '/materials',
    );
  });

  test('firstReadyMaterial skips materials that still need AI review', () {
    final ready = _material(id: 'material_ready', status: MaterialStatus.ready);

    expect(
      firstReadyMaterial(<CourseMaterial>[
        _material(status: MaterialStatus.processing),
        _material(status: MaterialStatus.needsReview),
        ready,
      ]),
      ready,
    );
  });
}

CourseMaterial _material({
  String id = 'material_1',
  MaterialStatus status = MaterialStatus.processing,
  String parseJobId = 'job_1',
}) {
  return CourseMaterial(
    id: id,
    childId: 'child_1',
    parseJobId: parseJobId,
    teacherName: '外教课',
    lessonDate: DateTime(2026, 5, 5),
    title: '待识别讲义',
    topic: '',
    status: status,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: '',
    tags: const <String>[],
  );
}
