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
  testWidgets('left swipe cancel keeps material and does not call delete',
      (tester) async {
    final repository =
        _FakeDeleteRepository(materials: <CourseMaterial>[_material()]);
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);

    await tester
        .tap(find.byKey(const ValueKey<String>('cancel-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, isEmpty);
    expect(find.byKey(const ValueKey<String>('material-card-material_1')),
        findsOneWidget);
  });

  testWidgets('left swipe confirm deletes material and refreshes list',
      (tester) async {
    final repository =
        _FakeDeleteRepository(materials: <CourseMaterial>[_material()]);
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);
    await tester
        .tap(find.byKey(const ValueKey<String>('confirm-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, <String>['material_1']);
    expect(find.text('还没有课程资料'), findsOneWidget);
  });

  testWidgets('successful delete hides stale material during refresh',
      (tester) async {
    final repository = _FakeDeleteRepository(
      materials: <CourseMaterial>[_material()],
      removeOnDelete: false,
    );
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);
    await tester
        .tap(find.byKey(const ValueKey<String>('confirm-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, <String>['material_1']);
    expect(find.byKey(const ValueKey<String>('material-card-material_1')),
        findsNothing);
    expect(find.text('还没有课程资料'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('delete failure restores material and shows Chinese error',
      (tester) async {
    final repository = _FakeDeleteRepository(
      materials: <CourseMaterial>[_material()],
      deleteError: DioException(
        requestOptions: RequestOptions(path: '/materials/material_1'),
        message: 'network failed',
      ),
    );
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);
    await tester
        .tap(find.byKey(const ValueKey<String>('confirm-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, <String>['material_1']);
    expect(find.text('删除失败，请稍后重试。'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('material-card-material_1')),
        findsOneWidget);
  });
}

Future<void> _pumpLibrary(
  WidgetTester tester,
  _FakeDeleteRepository repository,
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
        path: '/materials/scan',
        builder: (context, state) => const Text('scan'),
      ),
      GoRoute(
        path: '/lessons/:materialId',
        builder: (context, state) =>
            Text('lesson:${state.pathParameters['materialId']}'),
      ),
      GoRoute(
        path: '/materials/review/:jobId',
        builder: (context, state) =>
            Text('review:${state.pathParameters['jobId']}'),
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

class _FakeDeleteRepository extends AppRepository {
  _FakeDeleteRepository({
    required this.materials,
    this.deleteError,
    this.removeOnDelete = true,
  }) : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  List<CourseMaterial> materials;
  final Object? deleteError;
  final bool removeOnDelete;
  final List<String> deletedMaterialIds = <String>[];

  @override
  Future<List<CourseMaterial>> listMaterials({required String childId}) async {
    return materials;
  }

  @override
  Future<void> deleteMaterial(String materialId) async {
    deletedMaterialIds.add(materialId);
    final error = deleteError;
    if (error != null) {
      throw error;
    }
    if (!removeOnDelete) {
      return;
    }
    materials =
        materials.where((material) => material.id != materialId).toList();
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

CourseMaterial _material() {
  return CourseMaterial(
    id: 'material_1',
    childId: 'child_1',
    parseJobId: 'job_1',
    teacherName: '外教课',
    lessonDate: DateTime(2026, 5, 15),
    title: 'Run, Hop, Go!',
    topic: 'Phonics Rr',
    status: MaterialStatus.ready,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: '',
    tags: const <String>[],
  );
}
