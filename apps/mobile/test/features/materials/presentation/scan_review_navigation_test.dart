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
    expect(find.text('拍照'), findsWidgets);
    expect(find.text('从相册选择'), findsWidgets);
    expect(find.text('开始识别'), findsOneWidget);
  });

  testWidgets('upload success navigates from scan page to AI review page',
      (tester) async {
    _useTallPhoneViewport(tester);
    final repository = _FakeAppRepository();
    final draftController = ScanDraftController()
      ..setPages(<XFile>[
        XFile('/tmp/worksheet.jpg', name: 'worksheet.jpg'),
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
      overrides: <Override>[
        activeChildProvider.overrideWithValue(_childProfile()),
        scanDraftProvider.overrideWith((ref) => draftController),
      ],
    );

    final uploadButton = find.widgetWithText(FilledButton, '开始识别');
    await tester.ensureVisible(uploadButton);
    await tester.tap(uploadButton);
    await tester.pumpAndSettle();

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
    await tester.ensureVisible(find.text('确认并生成课程详情'));
    await tester.tap(find.text('确认并生成课程详情'));
    await tester.pumpAndSettle();

    expect(repository.confirmCalls, 1);
    expect(find.text('lesson:material_1'), findsOneWidget);
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
  await tester.pumpAndSettle();
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

  @override
  Future<MaterialCreateResult> uploadMaterial({
    required String childId,
    required String teacherName,
    required DateTime lessonDate,
    required String title,
    required String topic,
    required List<XFile> files,
  }) async {
    uploadCalls += 1;
    return MaterialCreateResult(
      material: _courseMaterial(status: MaterialStatus.processing),
      job: _materialJob(status: JobStatus.needsReview),
    );
  }

  @override
  Future<MaterialParseJob> getMaterialJob(String jobId) async {
    return _materialJob(status: JobStatus.needsReview);
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
  );
}
