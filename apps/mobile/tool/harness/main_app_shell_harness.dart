import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';

import 'package:learning_english_mobile/app/shell/app_shell.dart';
import 'package:learning_english_mobile/core/theme/app_theme.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/reports/presentation/reports_screen.dart';
import 'package:learning_english_mobile/features/speaking/presentation/speaking_partner_screen.dart';

const _screen = String.fromEnvironment('HARNESS_SCREEN', defaultValue: 'reports');
const _imageUrl = String.fromEnvironment('HARNESS_IMAGE_URL');
const _ttsUsUrl = String.fromEnvironment('HARNESS_TTS_US_URL');
const _ttsUkUrl = String.fromEnvironment('HARNESS_TTS_UK_URL');

void main() {
  runApp(
    ProviderScope(
      overrides: <Override>[
        appRepositoryProvider.overrideWithValue(
          _HarnessRepository(
            imageUrl: _imageUrl,
            ttsUsUrl: _ttsUsUrl,
            ttsUkUrl: _ttsUkUrl,
          ),
        ),
        activeChildProvider.overrideWithValue(_child()),
        weeklyReportProvider.overrideWith((ref) async => _weeklyReport()),
        lastSpeakingAttemptProvider.overrideWith((ref) {
          return _screen == 'speaking' ? _speakingAttempt() : null;
        }),
      ],
      child: const _HarnessApp(),
    ),
  );
}

class _HarnessApp extends StatelessWidget {
  const _HarnessApp();

  @override
  Widget build(BuildContext context) {
    final initialLocation = switch (_screen) {
      'lesson' => '/lessons/material_dashscope_real',
      'speaking' => '/review/speaking/material_dashscope_real',
      _ => '/reports',
    };
    final router = GoRouter(
      initialLocation: initialLocation,
      routes: <RouteBase>[
        ShellRoute(
          builder: (context, state, child) => AppShell(
            location: state.uri.path,
            child: child,
          ),
          routes: <RouteBase>[
            GoRoute(
              path: '/lessons/:materialId',
              builder: (context, state) => LessonDetailScreen(
                materialId: state.pathParameters['materialId'] ?? '',
              ),
            ),
            GoRoute(
              path: '/reports',
              builder: (context, state) => const ReportsScreen(),
            ),
            GoRoute(
              path: '/review/speaking/:materialId',
              builder: (context, state) => SpeakingPartnerScreen(
                materialId: state.pathParameters['materialId'] ?? '',
              ),
            ),
          ],
        ),
      ],
    );
    return MaterialApp.router(
      title: 'LearningEnglish Harness',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      routerConfig: router,
    );
  }
}

ChildProfile _child() {
  return const ChildProfile(
    id: 'child_harness',
    name: 'Mia',
    avatarUrl: '',
    age: 6,
    level: 'starter',
    learningGoal: '课后复习更稳定',
    preferredReviewDurationMinutes: 10,
    parentNotes: '',
  );
}

WeeklyReport _weeklyReport() {
  return WeeklyReport(
    id: 'report_harness',
    childId: 'child_harness',
    weekStart: DateTime(2026, 5, 25),
    weekEnd: DateTime(2026, 5, 31),
    completedSessions: 1,
    reviewedWords: 2,
    speakingAttempts: 1,
    weakItems: const <String>['A rabbit can hop fast.'],
    recommendedActions: const <String>['先听标准音，再看图跟读 3 遍。'],
    reportSummary: '本周覆盖 1 份讲义、2 个学习资产；已掌握 1 个，需加强 1 个。',
    materialSummaries: const <MaterialReportSummary>[
      MaterialReportSummary(
        materialId: 'material_dashscope_real',
        title: 'Run, Hop, Go!',
        topic: 'Phonics Rr',
        assetCount: 2,
        completedReviewTasks: 1,
        pendingReviewTasks: 1,
        speakingAttempts: 1,
        averageSpeakingScore: 92,
      ),
    ],
    assetMastery: const <LearningAssetMastery>[
      LearningAssetMastery(
        assetId: 'asset_rabbit',
        materialId: 'material_dashscope_real',
        materialTitle: 'Run, Hop, Go!',
        text: 'rabbit',
        kind: 'word',
        translation: '兔子',
        imageUrl: '',
        audioUrl: '',
        masteryScore: 98,
        masteryStatus: 'mastered',
        reviewAttempts: 1,
        completedReviewTasks: 1,
        pendingReviewTasks: 0,
        speakingAttempts: 1,
        bestSpeakingScore: 92,
        lastSpeakingScore: 92,
        weakPoints: <String>[],
        recommendedAction: '保持当前节奏，下一次复习时快速过一遍。',
      ),
      LearningAssetMastery(
        assetId: 'asset_sentence',
        materialId: 'material_dashscope_real',
        materialTitle: 'Run, Hop, Go!',
        text: 'A rabbit can hop fast.',
        kind: 'sentence',
        translation: '兔子能跳得很快。',
        imageUrl: '',
        audioUrl: '',
        masteryScore: 20,
        masteryStatus: 'needs_practice',
        reviewAttempts: 1,
        completedReviewTasks: 0,
        pendingReviewTasks: 1,
        speakingAttempts: 0,
        weakPoints: <String>['A rabbit can hop fast.'],
        recommendedAction: '先听标准音，再看图跟读 3 遍。',
      ),
    ],
  );
}

SpeakingAttempt _speakingAttempt() {
  return SpeakingAttempt(
    id: 'attempt_dashscope_worker',
    childId: 'child_harness',
    materialId: 'material_dashscope_real',
    learningAssetId: 'asset_hello',
    promptText: '跟读：Hello world.',
    targetText: 'Hello world.',
    audioUrl:
        'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav',
    audioObjectKey: 'speaking_attempt/attempt_dashscope_worker/input.wav',
    audioContentType: 'audio/wav',
    audioSizeBytes: 128480,
    transcript: 'Hello word, 这里是阿里巴巴语音实验室。',
    pronunciationScore: 0.42,
    overallScore: 35,
    accuracyScore: 40,
    fluencyScore: 50,
    completenessScore: 50,
    feedback: '发音基本可辨，但存在明显错误和多余内容，未完整复述目标句子。',
    wordFeedback: const <SpeakingWordFeedback>[
      SpeakingWordFeedback(
        word: 'Hello',
        score: 95,
        status: 'good',
        tip: '发音准确，语调自然。',
      ),
      SpeakingWordFeedback(
        word: 'world',
        score: 20,
        status: 'needs_practice',
        tip: "误读为 'word'，需要补足 /l/ 和结尾音。",
      ),
    ],
    suggestions: const <String>[
      "重点练习 world 的发音：/wɜːrld/，注意 /r/ 和 /l/ 连读。",
    ],
    provider: 'dashscope',
    status: SpeakingAttemptStatus.scored,
    createdAt: DateTime(2026, 5, 27, 0, 11, 50),
    updatedAt: DateTime(2026, 5, 27, 0, 11, 57),
  );
}

class _HarnessRepository extends AppRepository {
  _HarnessRepository({
    required this.imageUrl,
    required this.ttsUsUrl,
    required this.ttsUkUrl,
  }) : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final String imageUrl;
  final String ttsUkUrl;
  final String ttsUsUrl;

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return CourseMaterial(
      id: materialId,
      childId: 'child_harness',
      parseJobId: 'job_harness',
      teacherName: 'Emma',
      lessonDate: DateTime(2026, 5, 25),
      title: 'Run, Hop, Go!',
      topic: 'Phonics Rr',
      status: MaterialStatus.ready,
      sourceImages: <String>[if (imageUrl.isNotEmpty) imageUrl],
      pdfUrl: '',
      ocrText: 'A rabbit can hop fast.',
      tags: const <String>['Phonics Rr'],
      imageRecords: <MaterialImageRecord>[
        MaterialImageRecord(
          id: 'image_record_1',
          pageIndex: 1,
          sourceType: 'gallery',
          originalFilename: 'worksheet-rabbit.png',
          url: imageUrl,
          objectKey: 'material/material_dashscope_real/worksheet-rabbit.png',
          contentType: 'image/png',
          sizeBytes: 128480,
          imageTitle: 'Run, Hop, Go!',
          ocrText: 'A rabbit can hop fast.',
          vocabulary: const <String>['rabbit'],
          sentences: const <String>['A rabbit can hop fast.'],
          details: const <String>['讲义图片与彩色配图已关联。'],
        ),
      ],
      learningAssets: <LearningAsset>[
        LearningAsset(
          id: 'asset_rabbit',
          text: 'rabbit',
          kind: 'word',
          translation: '兔子',
          sourcePageIndex: 1,
          sourceVisualDescription: 'A rabbit can hop fast.',
          pronunciationText: 'rabbit',
          imagePrompt: 'Colorful child-friendly rabbit flashcard.',
          generatedImageStatus: 'ready',
          generatedImageUrl: imageUrl,
          generatedImageObjectKey:
              'generated/media/material_dashscope_real/asset_rabbit/image.png',
          ttsUsStatus: 'ready',
          ttsUsUrl: ttsUsUrl,
          ttsUsObjectKey:
              'generated/media/material_dashscope_real/asset_rabbit/tts-us.mp3',
          ttsUkStatus: 'ready',
          ttsUkUrl: ttsUkUrl,
          ttsUkObjectKey:
              'generated/media/material_dashscope_real/asset_rabbit/tts-uk.mp3',
          primaryAccent: 'us',
        ),
      ],
    );
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    return KnowledgePack(
      id: 'knowledge_harness',
      materialId: materialId,
      topic: 'Phonics Rr',
      difficultyBand: DifficultyBand.repeat,
      lessonSummary: '本课复习 rabbit 的看图跟读。',
      reviewRecommendation: '先看彩色配图，再听英美音标准发音。',
      vocabularyItems: const <VocabularyItem>[
        VocabularyItem(
          id: 'word_rabbit',
          knowledgePackId: 'knowledge_harness',
          word: 'rabbit',
          phonics: '',
          meaningCn: '兔子',
          imageUrl: '',
          audioUrl: '',
          exampleSentence: 'A rabbit can hop fast.',
        ),
      ],
      sentencePatterns: const <SentencePattern>[
        SentencePattern(
          id: 'sentence_rabbit',
          knowledgePackId: 'knowledge_harness',
          sentence: 'A rabbit can hop fast.',
          meaningCn: '兔子能跳得很快。',
          usageType: '跟读句型',
          audioUrl: '',
        ),
      ],
    );
  }

  @override
  Future<CourseMaterial> updateLearningAssetPrimaryAccent({
    required String materialId,
    required String assetId,
    required String primaryAccent,
  }) async {
    return getMaterial(materialId);
  }
}
