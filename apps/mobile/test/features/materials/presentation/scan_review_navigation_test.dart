import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/data/scan_draft_controller.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_review_screen.dart';
import 'package:learning_english_mobile/features/materials/presentation/scan_upload_screen.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';

void main() {
  testWidgets('scan page is image-first and does not require metadata form',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
    final router = GoRouter(
      initialLocation: '/materials/scan',
      routes: <RouteBase>[
        GoRoute(
          path: '/materials/scan',
          builder: (context, state) => const ScanUploadScreen(),
        ),
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
      overrides: <Override>[
        activeChildProvider.overrideWithValue(_childProfile()),
      ],
    );

    expect(find.text('课程标题'), findsNothing);
    expect(find.text('老师名'), findsNothing);
    expect(find.text('主题'), findsNothing);
    expect(find.text('拍照'), findsOneWidget);
    expect(find.text('从相册选择'), findsOneWidget);
    expect(find.text('添加讲义页'), findsOneWidget);
    expect(find.text('先添加讲义页'), findsOneWidget);
    expect(find.text('拍照上传'), findsNothing);
  });

  testWidgets('upload success navigates from scan page to AI review page',
      (tester) async {
    _useTallPhoneViewport(tester);
    final worksheetBytes = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
    );
    final repository = _FakeAppRepository();
    final draftController = ScanDraftController()
      ..setPages(<ScanDraftPage>[
        ScanDraftPage(
          file: XFile.fromData(
            worksheetBytes,
            name: 'gallery-worksheet.jpg',
            mimeType: 'image/png',
          ),
          sourceType: 'gallery',
        ),
      ]);

    final router = GoRouter(
      initialLocation: '/materials/scan',
      routes: <RouteBase>[
        GoRoute(
          path: '/materials/scan',
          builder: (context, state) => const ScanUploadScreen(),
        ),
        GoRoute(
          path: '/materials/review/:jobId',
          builder: (context, state) => Text(
            'review:${state.pathParameters['jobId']}:'
            '${state.uri.queryParameters['materialId']}',
          ),
        ),
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
      settle: false,
      overrides: <Override>[
        activeChildProvider.overrideWithValue(_childProfile()),
        scanDraftProvider.overrideWith((ref) => draftController),
      ],
    );
    await tester.pump();

    expect(find.text('已添加 1 页'), findsOneWidget);
    expect(find.text('相册选择'), findsOneWidget);
    expect(find.text('第 1 页'), findsOneWidget);
    expect(find.text('gallery-worksheet.jpg'), findsNothing);
    expect(find.byType(Image), findsWidgets);
    expect(find.text('继续拍照'), findsOneWidget);
    expect(find.text('继续选择'), findsOneWidget);
    final uploadButton = find.widgetWithText(FilledButton, '开始识别');
    await tester.tap(uploadButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(repository.uploadCalls, 1);
    expect(find.text('review:job_1:material_1'), findsOneWidget);
  });

  testWidgets('AI review confirmation navigates to lesson detail',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
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

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    expect(find.text('AI 识别结果'), findsOneWidget);
    expect(find.text('图片记录'), findsOneWidget);
    expect(find.textContaining('Animals page'), findsOneWidget);
    expect(find.textContaining('单词：cat、dog、bird'), findsOneWidget);
    await tester.ensureVisible(find.text('确认并生成课程详情'));
    await tester.tap(find.text('确认并生成课程详情'));
    await tester.pumpAndSettle();

    expect(repository.confirmCalls, 1);
    expect(find.text('lesson:material_1'), findsOneWidget);
  });

  testWidgets('AI review page auto refreshes processing jobs', (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository()
      ..jobStatuses = <JobStatus>[
        JobStatus.processing,
        JobStatus.processing,
        JobStatus.processing,
        JobStatus.needsReview,
      ];
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
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    expect(find.text('AI 正在处理中'), findsOneWidget);
    expect(repository.getMaterialJobCalls, 1);

    await tester.pump(const Duration(seconds: 4));
    expect(repository.getMaterialJobCalls, 2);
    expect(find.text('AI 正在处理中'), findsOneWidget);

    await tester.pump(const Duration(seconds: 3));
    expect(repository.getMaterialJobCalls, 3);
    expect(find.text('AI 正在处理中'), findsOneWidget);

    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    expect(repository.getMaterialJobCalls, 4);
    expect(find.text('AI 识别结果'), findsOneWidget);
  });

  testWidgets('AI review page shows learning assets with source page label',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
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
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    expect(find.text('核心学习资产'), findsOneWidget);
    expect(find.text('queen'), findsWidgets);
    expect(find.text('女王'), findsOneWidget);
    expect(find.textContaining('单词 · 第 1 页'), findsOneWidget);
    expect(find.text('读 queen。'), findsOneWidget);
  });

  testWidgets('lesson detail keeps source image records', (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
    final router = GoRouter(
      initialLocation: '/lessons/material_1',
      routes: <RouteBase>[
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) => LessonDetailScreen(
            materialId: state.pathParameters['materialId'] ?? '',
          ),
        ),
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    expect(find.text('原始讲义记录'), findsOneWidget);
    expect(find.textContaining('第 1 页 · Animals page'), findsOneWidget);
    expect(find.textContaining('句子：It is a cat.'), findsOneWidget);
    expect(find.textContaining('细节：图片中包含动物词汇。'), findsOneWidget);
  });

  testWidgets('lesson detail shows learning asset media and tts status',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
    final router = GoRouter(
      initialLocation: '/lessons/material_1',
      routes: <RouteBase>[
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) => LessonDetailScreen(
            materialId: state.pathParameters['materialId'] ?? '',
          ),
        ),
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    expect(find.text('核心学习资产'), findsOneWidget);
    expect(find.text('queen'), findsWidgets);
    expect(find.text('女王'), findsOneWidget);
    expect(find.text('美式'), findsOneWidget);
    expect(find.text('英式'), findsOneWidget);
    expect(find.textContaining('配图：已生成'), findsOneWidget);
    expect(find.textContaining('美式：已生成 · 英式：已生成'), findsOneWidget);
  });

  testWidgets('lesson detail shows error when primary accent update fails',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository()..failPrimaryAccentUpdate = true;
    final router = GoRouter(
      initialLocation: '/lessons/material_1',
      routes: <RouteBase>[
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) => LessonDetailScreen(
            materialId: state.pathParameters['materialId'] ?? '',
          ),
        ),
      ],
    );

    await _pumpTestApp(
      tester,
      router: router,
      repository: repository,
    );

    await tester.tap(find.text('英式'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('发音切换失败，请稍后重试。'), findsOneWidget);
  });
}

void _useTallPhoneViewport(WidgetTester tester) {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 1600);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Future<void> _pumpTestApp(
  WidgetTester tester, {
  required GoRouter router,
  required _FakeAppRepository repository,
  bool settle = true,
  List<Override> overrides = const <Override>[],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        appRepositoryProvider.overrideWithValue(repository),
        ...overrides,
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  }
}

class _FakeAppRepository extends AppRepository {
  _FakeAppRepository()
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  var uploadCalls = 0;
  var confirmCalls = 0;
  var getMaterialJobCalls = 0;
  List<JobStatus>? jobStatuses;
  var failPrimaryAccentUpdate = false;

  @override
  Future<MaterialCreateResult> uploadMaterial({
    required String childId,
    required String teacherName,
    required DateTime lessonDate,
    required String title,
    required String topic,
    required List<ScanDraftPage> files,
  }) async {
    uploadCalls += 1;
    return MaterialCreateResult(
      material: _courseMaterial(status: MaterialStatus.processing),
      job: _materialJob(status: JobStatus.needsReview),
    );
  }

  @override
  Future<MaterialParseJob> getMaterialJob(String jobId) async {
    getMaterialJobCalls += 1;
    final statuses = jobStatuses;
    if (statuses != null && statuses.isNotEmpty) {
      final index = (getMaterialJobCalls - 1).clamp(0, statuses.length - 1);
      return _materialJob(status: statuses[index]);
    }
    return _materialJob(status: JobStatus.needsReview);
  }

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return _courseMaterial(status: MaterialStatus.ready);
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
    confirmCalls += 1;
    return _materialJob(status: JobStatus.ready);
  }

  @override
  Future<CourseMaterial> updateLearningAssetPrimaryAccent({
    required String materialId,
    required String assetId,
    required String primaryAccent,
  }) async {
    if (failPrimaryAccentUpdate) {
      throw DioException(
        requestOptions: RequestOptions(path: '/materials/$materialId'),
        error: 'network failed',
      );
    }
    return _courseMaterial(status: MaterialStatus.ready);
  }
}

ChildProfile _childProfile() {
  return const ChildProfile(
    id: 'child_1',
    name: 'Mia',
    avatarUrl: '',
    age: 6,
    level: 'starter',
    learningGoal: '课后复习更稳定',
    preferredReviewDurationMinutes: 10,
    parentNotes: '',
  );
}

CourseMaterial _courseMaterial({required MaterialStatus status}) {
  return CourseMaterial(
    id: 'material_1',
    childId: 'child_1',
    parseJobId: 'job_1',
    teacherName: 'Emma',
    lessonDate: DateTime(2026, 4, 29),
    title: 'Animals Around Me',
    topic: '动物',
    status: status,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: 'cat dog bird',
    tags: const <String>['动物'],
    imageRecords: _imageRecords(),
    learningAssets: _learningAssets(),
  );
}

MaterialParseJob _materialJob({required JobStatus status}) {
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
    draftSentences: const <String>['It is a cat.', 'I can see a dog.'],
    draftImageRecords: _imageRecords(),
    draftLearningAssets: _learningAssets(),
  );
}

List<MaterialImageRecord> _imageRecords() {
  return const <MaterialImageRecord>[
    MaterialImageRecord(
      id: 'image_1',
      pageIndex: 1,
      sourceType: 'camera',
      originalFilename: 'worksheet.jpg',
      url: '',
      objectKey: 'materials/material_1/worksheet.jpg',
      contentType: 'image/jpeg',
      sizeBytes: 1024,
      imageTitle: 'Animals page',
      ocrText: 'cat dog bird',
      vocabulary: <String>['cat', 'dog', 'bird'],
      sentences: <String>['It is a cat.'],
      details: <String>['图片中包含动物词汇。'],
    ),
  ];
}

List<LearningAsset> _learningAssets() {
  return const <LearningAsset>[
    LearningAsset(
      id: 'asset_queen',
      text: 'queen',
      kind: 'word',
      translation: '女王',
      sourcePageIndex: 1,
      sourceBbox:
          SourceBoundingBox(x: 0.05, y: 0.14, width: 0.43, height: 0.35),
      sourceVisualDescription: '迷宫里的女王。',
      pronunciationText: 'queen',
      imagePrompt: '参考讲义生成彩色图。',
      difficulty: 'easy',
      teachingNote: '读 queen。',
      isCore: true,
      generatedImageStatus: 'ready',
      generatedImageUrl: '',
      generatedImageObjectKey: 'mock_media/hn014/images/queen.svg',
      ttsUsStatus: 'ready',
      ttsUsUrl: 'http://127.0.0.1:8000/mock-media/hn014/tts/us/queen.m4a',
      ttsUsObjectKey: 'mock_media/hn014/tts/us/queen.m4a',
      ttsUkStatus: 'ready',
      ttsUkUrl: 'http://127.0.0.1:8000/mock-media/hn014/tts/uk/queen.m4a',
      ttsUkObjectKey: 'mock_media/hn014/tts/uk/queen.m4a',
      primaryAccent: 'us',
    ),
  ];
}

KnowledgePack _knowledgePack() {
  return KnowledgePack(
    id: 'knowledge_1',
    materialId: 'material_1',
    topic: '动物',
    difficultyBand: DifficultyBand.repeat,
    lessonSummary: '本课复习 cat、dog、bird。',
    reviewRecommendation: '先看图认词，再练句子。',
    vocabularyItems: const <VocabularyItem>[
      VocabularyItem(
        id: 'word_1',
        knowledgePackId: 'knowledge_1',
        word: 'cat',
        meaningCn: '猫',
        exampleSentence: 'It is a cat.',
        phonics: '',
        imageUrl: '',
        audioUrl: '',
      ),
    ],
    sentencePatterns: const <SentencePattern>[
      SentencePattern(
        id: 'sentence_1',
        knowledgePackId: 'knowledge_1',
        sentence: 'It is a cat.',
        meaningCn: '它是一只猫。',
        usageType: 'answer',
        audioUrl: '',
      ),
    ],
  );
}
