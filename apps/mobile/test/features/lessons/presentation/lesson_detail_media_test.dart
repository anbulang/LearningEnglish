import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

void main() {
  testWidgets('lesson detail shows Chinese media failure reasons',
      (tester) async {
    final repository = _LessonMediaRepository(
      material: _material(
        asset: _asset(
          generatedImageStatus: 'failed',
          generatedImageError: '图片生成失败：provider timeout',
          ttsUsStatus: 'ready',
          ttsUsUrl: 'https://example.test/us.m4a',
          ttsUkStatus: 'failed',
          ttsUkError: '英式发音生成失败：provider timeout',
        ),
      ),
    );

    await tester.pumpWidget(_lessonDetailApp(repository));
    await tester.pumpAndSettle();

    expect(find.text('图片生成失败：provider timeout'), findsOneWidget);
    expect(find.text('英式发音生成失败：provider timeout'), findsOneWidget);
  });

  testWidgets('lesson detail prevents switching to unavailable accent',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final repository = _LessonMediaRepository(
      material: _material(
        asset: _asset(
          ttsUsStatus: 'ready',
          ttsUsUrl: 'https://example.test/us.m4a',
          ttsUkStatus: 'failed',
          ttsUkError: '英式发音暂不可用',
          primaryAccent: 'us',
        ),
      ),
    );

    await tester.pumpWidget(_lessonDetailApp(repository));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('英式'));
    await tester.tap(find.text('英式'));
    await tester.pumpAndSettle();

    expect(repository.updatedAccent, isNull);
    expect(find.text('英式发音暂不可用'), findsOneWidget);
  });

  testWidgets('lesson detail allows legacy URL-only accent switch',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final repository = _LessonMediaRepository(
      material: _material(
        asset: _asset(
          ttsUsStatus: 'ready',
          ttsUsUrl: 'https://example.test/us.m4a',
          ttsUkStatus: 'pending',
          ttsUkUrl: 'https://example.test/uk.m4a',
          ttsUkError: '英式发音暂不可用',
          primaryAccent: 'us',
        ),
      ),
    );

    await tester.pumpWidget(_lessonDetailApp(repository));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('英式'));
    await tester.tap(find.text('英式'));
    await tester.pumpAndSettle();

    expect(repository.updatedAccent, 'uk');
    expect(find.text('英式发音暂不可用'), findsNothing);
  });
}

Widget _lessonDetailApp(_LessonMediaRepository repository) {
  final router = GoRouter(
    initialLocation: '/lessons/material_1',
    routes: <RouteBase>[
      GoRoute(
        path: '/lessons/:materialId',
        builder: (context, state) => LessonDetailScreen(
          materialId: state.pathParameters['materialId']!,
        ),
      ),
    ],
  );

  return ProviderScope(
    overrides: <Override>[
      appRepositoryProvider.overrideWithValue(repository),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

class _LessonMediaRepository extends AppRepository {
  _LessonMediaRepository({required this.material})
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final CourseMaterial material;
  String? updatedAccent;

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return material;
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    return _knowledgePack();
  }

  @override
  Future<CourseMaterial> updateLearningAssetPrimaryAccent({
    required String materialId,
    required String assetId,
    required String primaryAccent,
  }) async {
    updatedAccent = primaryAccent;
    return material;
  }
}

CourseMaterial _material({required LearningAsset asset}) {
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
    learningAssets: <LearningAsset>[asset],
  );
}

LearningAsset _asset({
  String generatedImageStatus = 'ready',
  String generatedImageError = '',
  String ttsUsStatus = 'ready',
  String ttsUsUrl = '',
  String ttsUsError = '',
  String ttsUkStatus = 'ready',
  String ttsUkUrl = '',
  String ttsUkError = '',
  String primaryAccent = 'us',
}) {
  return LearningAsset(
    id: 'asset_1',
    text: 'queen',
    kind: 'word',
    translation: '女王',
    sourcePageIndex: 1,
    pronunciationText: 'queen',
    isCore: true,
    generatedImageStatus: generatedImageStatus,
    generatedImageError: generatedImageError,
    ttsUsStatus: ttsUsStatus,
    ttsUsUrl: ttsUsUrl,
    ttsUsError: ttsUsError,
    ttsUkStatus: ttsUkStatus,
    ttsUkUrl: ttsUkUrl,
    ttsUkError: ttsUkError,
    primaryAccent: primaryAccent,
  );
}

KnowledgePack _knowledgePack() {
  return KnowledgePack(
    id: 'knowledge_1',
    materialId: 'material_1',
    topic: '动物',
    difficultyBand: DifficultyBand.repeat,
    lessonSummary: '本课复习 queen。',
    reviewRecommendation: '先看图认词，再练句子。',
    vocabularyItems: const <VocabularyItem>[
      VocabularyItem(
        id: 'word_1',
        knowledgePackId: 'knowledge_1',
        word: 'queen',
        meaningCn: '女王',
        exampleSentence: 'It is a queen.',
        phonics: '',
        imageUrl: '',
        audioUrl: '',
      ),
    ],
    sentencePatterns: const <SentencePattern>[
      SentencePattern(
        id: 'sentence_1',
        knowledgePackId: 'knowledge_1',
        sentence: 'It is a queen.',
        meaningCn: '它是一位女王。',
        usageType: 'answer',
        audioUrl: '',
      ),
    ],
  );
}
