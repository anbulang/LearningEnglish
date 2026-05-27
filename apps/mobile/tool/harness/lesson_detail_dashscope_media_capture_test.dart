import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/core/theme/app_theme.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

void main() {
  testWidgets('capture HN-016A DashScope lesson detail media evidence',
      (tester) async {
    final evidenceRoot = Directory(
      '/Users/chaucermini/Code/LearningEnglish/dist/harness/HN-016A',
    );
    final imageFile = File(
      '${evidenceRoot.path}/worker-storage/generated/media/material_dashscope_real/asset_rabbit/image.png',
    );
    final ttsUsFile = File(
      '${evidenceRoot.path}/worker-storage/generated/media/material_dashscope_real/asset_rabbit/tts-us.mp3',
    );
    final ttsUkFile = File(
      '${evidenceRoot.path}/worker-storage/generated/media/material_dashscope_real/asset_rabbit/tts-uk.mp3',
    );
    expect(imageFile.existsSync(), isTrue);
    expect(ttsUsFile.existsSync(), isTrue);
    expect(ttsUkFile.existsSync(), isTrue);

    final boundaryKey = GlobalKey();
    await tester.binding.setSurfaceSize(const Size(390, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final repository = _LessonMediaRepository(
      imageDataUrl: _pngDataUrl(imageFile),
      ttsUsUrl: 'file://${ttsUsFile.path}',
      ttsUkUrl: 'file://${ttsUkFile.path}',
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appRepositoryProvider.overrideWithValue(repository),
        ],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: RepaintBoundary(
            key: boundaryKey,
            child: const LessonDetailScreen(
              materialId: 'material_dashscope_real',
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('核心学习资产'), findsOneWidget);
    expect(find.text('rabbit'), findsWidgets);
    expect(find.text('配图：已生成'), findsOneWidget);
    expect(find.text('美式：已生成 · 英式：已生成'), findsOneWidget);

    final output =
        File('${evidenceRoot.path}/lesson-detail-dashscope-media-screen.png');
    await tester.runAsync(() async {
      final boundary = boundaryKey.currentContext!.findRenderObject()!
          as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 2);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      output.writeAsBytesSync(data!.buffer.asUint8List());
      final summaryText = const JsonEncoder.withIndent('  ').convert(
        <String, dynamic>{
          'material_id': 'material_dashscope_real',
          'asset_id': 'asset_rabbit',
          'generated_image': imageFile.path,
          'generated_image_size_bytes': imageFile.lengthSync(),
          'tts_us': ttsUsFile.path,
          'tts_us_size_bytes': ttsUsFile.lengthSync(),
          'tts_uk': ttsUkFile.path,
          'tts_uk_size_bytes': ttsUkFile.lengthSync(),
          'screenshot': output.path,
          'ui_assertions': <String>[
            '核心学习资产',
            '配图：已生成',
            '美式：已生成 · 英式：已生成',
          ],
        },
      );
      File('${evidenceRoot.path}/lesson-detail-dashscope-media-summary.json')
          .writeAsStringSync('$summaryText\n');
    });
    expect(output.existsSync(), isTrue);
  });
}

String _pngDataUrl(File file) {
  return 'data:image/png;base64,${base64Encode(file.readAsBytesSync())}';
}

class _LessonMediaRepository extends AppRepository {
  _LessonMediaRepository({
    required this.imageDataUrl,
    required this.ttsUsUrl,
    required this.ttsUkUrl,
  }) : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final String imageDataUrl;
  final String ttsUkUrl;
  final String ttsUsUrl;

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return CourseMaterial(
      id: materialId,
      childId: 'child_hn016a',
      parseJobId: 'job_hn016a',
      teacherName: 'Emma',
      lessonDate: DateTime(2026, 5, 25),
      title: 'Run, Hop, Go!',
      topic: 'Phonics Rr',
      status: MaterialStatus.ready,
      sourceImages: const <String>[],
      pdfUrl: '',
      ocrText: 'rabbit',
      tags: const <String>['Phonics Rr'],
      learningAssets: <LearningAsset>[
        LearningAsset(
          id: 'asset_rabbit',
          text: 'rabbit',
          kind: 'word',
          translation: '兔子',
          sourcePageIndex: 1,
          sourceVisualDescription:
              'A colorful rabbit illustration generated from worksheet content.',
          pronunciationText: 'rabbit',
          imagePrompt: 'Colorful child-friendly rabbit flashcard.',
          generatedImageStatus: 'ready',
          generatedImageUrl: imageDataUrl,
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
      id: 'knowledge_hn016a',
      materialId: materialId,
      topic: 'Phonics Rr',
      difficultyBand: DifficultyBand.repeat,
      lessonSummary: '本课复习 rabbit 的看图跟读。',
      reviewRecommendation: '先看彩色配图，再听英美音标准发音。',
      vocabularyItems: const <VocabularyItem>[
        VocabularyItem(
          id: 'word_rabbit',
          knowledgePackId: 'knowledge_hn016a',
          word: 'rabbit',
          phonics: '',
          meaningCn: '兔子',
          imageUrl: '',
          audioUrl: '',
          exampleSentence: 'A rabbit can hop fast.',
        ),
      ],
      sentencePatterns: const <SentencePattern>[],
    );
  }
}
