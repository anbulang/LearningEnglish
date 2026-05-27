import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart'
    show
        ChildProfile,
        LearningAssetMastery,
        MaterialReportSummary,
        WeeklyReport;
import 'package:learning_english_mobile/core/theme/app_theme.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/reports/presentation/reports_screen.dart';

void main() {
  testWidgets('capture HN-018 reports screen evidence', (tester) async {
    final boundaryKey = GlobalKey();
    await tester.binding.setSurfaceSize(const Size(390, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          activeChildProvider.overrideWithValue(_child()),
          weeklyReportProvider.overrideWith((ref) async => _weeklyReport()),
        ],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: RepaintBoundary(
            key: boundaryKey,
            child: const ReportsScreen(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 300));

    final boundary = boundaryKey.currentContext!.findRenderObject()!
        as RenderRepaintBoundary;
    final output = File(
      '/Users/chaucermini/Code/LearningEnglish/dist/harness/HN-018/reports-screen.png',
    );
    await tester.runAsync(() async {
      final image = await boundary.toImage(pixelRatio: 2);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      output.parent.createSync(recursive: true);
      output.writeAsBytesSync(data!.buffer.asUint8List());
    });

    expect(output.existsSync(), isTrue);
  });
}

ChildProfile _child() {
  return const ChildProfile(
    id: 'child_hn018',
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
    id: 'report_hn018',
    childId: 'child_hn018',
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
        materialId: 'material_hn018',
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
        materialId: 'material_hn018',
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
        materialId: 'material_hn018',
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
