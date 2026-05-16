import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

void main() {
  testWidgets('deleted material detail shows Chinese not-found state',
      (tester) async {
    final repository = _DeletedMaterialRepository();
    final router = GoRouter(
      initialLocation: '/lessons/material_deleted',
      routes: <RouteBase>[
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) => LessonDetailScreen(
            materialId: state.pathParameters['materialId']!,
          ),
        ),
        GoRoute(
          path: '/materials',
          builder: (context, state) => const Text('materials-list'),
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

    expect(find.text('课程资料不存在或已删除'), findsOneWidget);
    expect(find.text('回到资料库'), findsOneWidget);

    await tester.tap(find.text('回到资料库'));
    await tester.pumpAndSettle();
    expect(find.text('materials-list'), findsOneWidget);
  });
}

class _DeletedMaterialRepository extends AppRepository {
  _DeletedMaterialRepository()
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    throw DioException(
      requestOptions: RequestOptions(path: '/materials/$materialId'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(path: '/materials/$materialId'),
        statusCode: 404,
        data: <String, dynamic>{'detail': 'Material not found'},
      ),
    );
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    throw DioException(
      requestOptions: RequestOptions(path: '/knowledge-packs/$materialId'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(path: '/knowledge-packs/$materialId'),
        statusCode: 404,
        data: <String, dynamic>{'detail': 'Knowledge pack not available yet'},
      ),
    );
  }
}
