import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_review_screen.dart';

void main() {
  testWidgets('parent edits title and deletes a wrong word before confirm',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 2200);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final repository = _EditReviewRepository();
    final router = GoRouter(
      initialLocation: '/materials/review/job_1?materialId=material_1',
      routes: <RouteBase>[
        GoRoute(
          path: '/materials/review/:jobId',
          builder: (context, state) => MaterialReviewScreen(
            jobId: state.pathParameters['jobId'] ?? '',
            materialId: state.uri.queryParameters['materialId'] ?? '',
          ),
        ),
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) =>
              Text('lesson:${state.pathParameters['materialId']}'),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appRepositoryProvider.overrideWithValue(repository),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    // Title and topic are editable fields seeded from the AI draft.
    await tester.enterText(
      find.widgetWithText(TextField, 'Animals Around Me'),
      '动物主题课',
    );

    // Vocabulary renders as editable chips (cat, dog, bird) + an add chip.
    expect(find.byType(InputChip), findsNWidgets(3));
    expect(find.widgetWithText(InputChip, 'dog'), findsOneWidget);

    // Delete the misrecognised word "dog" via its chip delete icon.
    final deleteDog = find.descendant(
      of: find.widgetWithText(InputChip, 'dog'),
      matching: find.byIcon(Icons.close_rounded),
    );
    await tester.ensureVisible(deleteDog);
    await tester.tap(deleteDog, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(find.widgetWithText(InputChip, 'dog'), findsNothing);

    await tester.ensureVisible(find.text('确认并生成课程详情'));
    await tester.tap(find.text('确认并生成课程详情'));
    await tester.pumpAndSettle();

    expect(repository.confirmedTitle, '动物主题课');
    expect(repository.confirmedVocabulary, <String>['cat', 'bird']);
    expect(find.text('lesson:material_1'), findsOneWidget);
  });

  testWidgets('parent corrects a mis-recognised word before confirm',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 2200);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final repository = _EditReviewRepository();
    await _pumpReview(tester, repository);

    // Tapping the "cat" chip opens the edit dialog seeded with the current word.
    await tester.tap(find.widgetWithText(InputChip, 'cat'));
    await tester.pumpAndSettle();
    final editField = find.descendant(
      of: find.byType(AlertDialog),
      matching: find.byType(TextField),
    );
    await tester.enterText(editField, 'cats');
    await tester.tap(find.widgetWithText(FilledButton, '保存'));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(InputChip, 'cats'), findsOneWidget);
    expect(find.widgetWithText(InputChip, 'cat'), findsNothing);

    await tester.ensureVisible(find.text('确认并生成课程详情'));
    await tester.tap(find.text('确认并生成课程详情'));
    await tester.pumpAndSettle();

    // The correction reaches the backend, not the original OCR word.
    expect(repository.confirmedVocabulary, <String>['cats', 'dog', 'bird']);
  });

  testWidgets('parent adds a new word before confirm', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 2200);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final repository = _EditReviewRepository();
    await _pumpReview(tester, repository);

    await tester.tap(find.widgetWithText(ActionChip, '添加单词'));
    await tester.pumpAndSettle();
    final addField = find.descendant(
      of: find.byType(AlertDialog),
      matching: find.byType(TextField),
    );
    await tester.enterText(addField, 'fish');
    await tester.tap(find.widgetWithText(FilledButton, '保存'));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(InputChip, 'fish'), findsOneWidget);

    await tester.ensureVisible(find.text('确认并生成课程详情'));
    await tester.tap(find.text('确认并生成课程详情'));
    await tester.pumpAndSettle();

    // The added word reaches the backend confirm payload.
    expect(
      repository.confirmedVocabulary,
      <String>['cat', 'dog', 'bird', 'fish'],
    );
  });
}

Future<void> _pumpReview(WidgetTester tester, AppRepository repository) async {
  final router = GoRouter(
    initialLocation: '/materials/review/job_1?materialId=material_1',
    routes: <RouteBase>[
      GoRoute(
        path: '/materials/review/:jobId',
        builder: (context, state) => MaterialReviewScreen(
          jobId: state.pathParameters['jobId'] ?? '',
          materialId: state.uri.queryParameters['materialId'] ?? '',
        ),
      ),
      GoRoute(
        path: '/lessons/:materialId',
        builder: (context, state) =>
            Text('lesson:${state.pathParameters['materialId']}'),
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        appRepositoryProvider.overrideWithValue(repository),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

class _EditReviewRepository extends AppRepository {
  _EditReviewRepository()
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  String? confirmedTitle;
  List<String>? confirmedVocabulary;

  @override
  Future<MaterialParseJob> getMaterialJob(String jobId) async {
    return _job(status: JobStatus.needsReview);
  }

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return _material();
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    return _knowledgePack();
  }

  @override
  Future<MaterialParseJob> confirmMaterialJob({
    required String jobId,
    required String draftTitle,
    required String draftTopic,
    required List<String> draftVocabulary,
    required List<String> draftSentences,
  }) async {
    confirmedTitle = draftTitle;
    confirmedVocabulary = draftVocabulary;
    return _job(status: JobStatus.ready);
  }
}

MaterialParseJob _job({required JobStatus status}) {
  return MaterialParseJob(
    id: 'job_1',
    materialId: 'material_1',
    status: status,
    confidenceSummary: '识别结果可信，建议家长确认核心词汇。',
    warnings: const <String>[],
    startedAt: DateTime(2026, 4, 29, 10),
    finishedAt: DateTime(2026, 4, 29, 10, 1),
    draftTitle: 'Animals Around Me',
    draftTopic: '动物',
    draftVocabulary: const <String>['cat', 'dog', 'bird'],
    draftSentences: const <String>['It is a cat.'],
    draftImageRecords: const <MaterialImageRecord>[],
    draftLearningAssets: const <LearningAsset>[],
  );
}

CourseMaterial _material() {
  return CourseMaterial(
    id: 'material_1',
    childId: 'child_1',
    parseJobId: 'job_1',
    teacherName: 'Emma',
    lessonDate: DateTime(2026, 4, 29),
    title: 'Animals Around Me',
    topic: '动物',
    status: MaterialStatus.ready,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: 'cat dog bird',
    tags: const <String>['动物'],
  );
}

KnowledgePack _knowledgePack() {
  return KnowledgePack(
    id: 'knowledge_1',
    materialId: 'material_1',
    topic: '动物',
    difficultyBand: DifficultyBand.repeat,
    lessonSummary: '本课复习 cat、bird。',
    reviewRecommendation: '先看图认词，再练句子。',
    vocabularyItems: const <VocabularyItem>[],
    sentencePatterns: const <SentencePattern>[],
  );
}
