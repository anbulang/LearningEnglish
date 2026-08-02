import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/home/presentation/home_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';

void main() {
  testWidgets('recent non-ready material opens AI review instead of lesson',
      (tester) async {
    final repository = _FakeHomeRepository(
      materials: <CourseMaterial>[
        _material(status: MaterialStatus.needsReview),
      ],
    );

    await _pumpHome(tester, repository);

    await tester.tap(find.text('待识别讲义').last);
    await tester.pumpAndSettle();

    expect(find.text('review:job_1:material_1'), findsOneWidget);
  });

  testWidgets('start review skips non-ready material and uses ready material',
      (tester) async {
    final repository = _FakeHomeRepository(
      materials: <CourseMaterial>[
        _material(id: 'material_processing', status: MaterialStatus.processing),
        _material(id: 'material_ready', status: MaterialStatus.ready),
      ],
    );

    await _pumpHome(tester, repository);

    await tester.tap(find.text('开始复习'));
    await tester.pumpAndSettle();

    expect(find.text('review-session:material_ready'), findsOneWidget);
  });
}

Future<void> _pumpHome(
  WidgetTester tester,
  _FakeHomeRepository repository,
) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 1600);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    initialLocation: '/home',
    routes: <RouteBase>[
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/materials/review/:jobId',
        builder: (context, state) => Text(
          'review:${state.pathParameters['jobId']}:'
          '${state.uri.queryParameters['materialId']}',
        ),
      ),
      GoRoute(
        path: '/lessons/:materialId',
        builder: (context, state) =>
            Text('lesson:${state.pathParameters['materialId']}'),
      ),
      GoRoute(
        path: '/review',
        builder: (context, state) => const Text('review'),
        routes: <RouteBase>[
          GoRoute(
            path: 'session/:materialId',
            builder: (context, state) =>
                Text('review-session:${state.pathParameters['materialId']}'),
          ),
        ],
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        appRepositoryProvider.overrideWithValue(repository),
        activeChildProvider.overrideWithValue(_childProfile()),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

class _FakeHomeRepository extends AppRepository {
  _FakeHomeRepository({required this.materials})
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final List<CourseMaterial> materials;

  @override
  Future<List<CourseMaterial>> listMaterials({required String childId}) async {
    return materials;
  }

  @override
  Future<List<ReviewTask>> listReviewTasks({
    required String childId,
    String? materialId,
    bool dueOnly = false,
  }) async {
    return const <ReviewTask>[];
  }

  @override
  Future<WeeklyReport> getWeeklyReport({required String childId}) async {
    return WeeklyReport(
      id: 'report_1',
      childId: childId,
      weekStart: DateTime(2026, 5, 18),
      weekEnd: DateTime(2026, 5, 24),
      completedSessions: 0,
      reviewedWords: 0,
      speakingAttempts: 0,
      weakItems: const <String>[],
      recommendedActions: const <String>[],
    );
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

CourseMaterial _material({
  String id = 'material_1',
  required MaterialStatus status,
}) {
  return CourseMaterial(
    id: id,
    childId: 'child_1',
    parseJobId: 'job_1',
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
