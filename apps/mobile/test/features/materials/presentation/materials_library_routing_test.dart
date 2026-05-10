import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/presentation/materials_library_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';

void main() {
  testWidgets('non-ready material opens AI review route', (tester) async {
    final repository = _FakeAppRepository(
      materials: <CourseMaterial>[
        _courseMaterial(
          status: MaterialStatus.failed,
          parseJobId: 'job_failed',
        ),
      ],
    );

    await _pumpLibrary(tester, repository);

    await tester
        .tap(find.byKey(const ValueKey<String>('material-card-material_1')));
    await tester.pumpAndSettle();

    expect(find.text('review:job_failed:material_1'), findsOneWidget);
  });

  testWidgets('ready material opens lesson detail route', (tester) async {
    final repository = _FakeAppRepository(
      materials: <CourseMaterial>[
        _courseMaterial(
          status: MaterialStatus.ready,
          parseJobId: 'job_ready',
        ),
      ],
    );

    await _pumpLibrary(tester, repository);

    await tester
        .tap(find.byKey(const ValueKey<String>('material-card-material_1')));
    await tester.pumpAndSettle();

    expect(find.text('lesson:material_1'), findsOneWidget);
  });
}

Future<void> _pumpLibrary(
  WidgetTester tester,
  _FakeAppRepository repository,
) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 1600);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    initialLocation: '/materials',
    routes: <RouteBase>[
      GoRoute(
        path: '/materials',
        builder: (context, state) => const MaterialsLibraryScreen(),
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

class _FakeAppRepository extends AppRepository {
  _FakeAppRepository({required this.materials})
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

CourseMaterial _courseMaterial({
  required MaterialStatus status,
  required String parseJobId,
}) {
  return CourseMaterial(
    id: 'material_1',
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
