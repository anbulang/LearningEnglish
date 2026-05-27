import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart'
    show
        ChildProfile,
        LearningAssetMastery,
        MaterialReportSummary,
        WeeklyReport;
import 'package:learning_english_mobile/core/theme/app_theme.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/profiles/presentation/profile_screen.dart';
import 'package:learning_english_mobile/features/reports/presentation/reports_screen.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';

void main() {
  testWidgets('报告页没有孩子档案时显示可操作空状态', (tester) async {
    await _pumpScreen(
      tester,
      const ReportsScreen(),
      overrides: <Override>[
        activeChildProvider.overrideWithValue(null),
      ],
    );

    expect(find.text('先添加孩子档案'), findsOneWidget);
    expect(find.text('报告加载失败'), findsNothing);
  });

  testWidgets('报告页显示学习资产掌握度和讲义汇总', (tester) async {
    await _pumpScreen(
      tester,
      const ReportsScreen(),
      overrides: <Override>[
        activeChildProvider.overrideWithValue(_child()),
        weeklyReportProvider.overrideWith((ref) async => _weeklyReport()),
      ],
    );

    expect(find.text('Mia 的本周学习概览'), findsOneWidget);
    expect(find.textContaining('2 个学习资产'), findsWidgets);
    expect(find.text('讲义汇总'), findsOneWidget);
    expect(find.text('Run, Hop, Go!'), findsOneWidget);
    expect(find.text('词句掌握度'), findsOneWidget);
    expect(find.text('rabbit'), findsOneWidget);
    expect(find.text('已掌握'), findsOneWidget);
    expect(find.text('需加强'), findsOneWidget);
  });

  testWidgets('我的页没有孩子档案时仍显示家长账号和添加入口', (tester) async {
    await _pumpScreen(
      tester,
      const ProfileScreen(),
      overrides: <Override>[
        currentParentProvider.overrideWithValue(_parent()),
        activeChildProvider.overrideWithValue(null),
      ],
    );

    expect(find.text('Chaucer'), findsOneWidget);
    expect(find.text('13800138000'), findsOneWidget);
    expect(find.text('先添加孩子档案'), findsOneWidget);
    expect(find.text('添加孩子档案'), findsOneWidget);
    expect(find.text('暂无孩子档案'), findsNothing);
  });
}

Future<void> _pumpScreen(
  WidgetTester tester,
  Widget screen, {
  List<Override> overrides = const <Override>[],
}) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 1200);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.light(),
        home: screen,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

ParentAccount _parent() {
  return const ParentAccount(
    id: 'parent_1',
    displayName: 'Chaucer',
    avatarUrl: '',
    phoneNumber: '13800138000',
  );
}

ChildProfile _child() {
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

WeeklyReport _weeklyReport() {
  return WeeklyReport(
    id: 'report_1',
    childId: 'child_1',
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
        materialId: 'material_1',
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
        materialId: 'material_1',
        materialTitle: 'Run, Hop, Go!',
        text: 'rabbit',
        kind: 'word',
        translation: '兔子',
        masteryScore: 98,
        masteryStatus: 'mastered',
        reviewAttempts: 1,
        completedReviewTasks: 1,
        pendingReviewTasks: 0,
        speakingAttempts: 1,
        bestSpeakingScore: 92,
        lastSpeakingScore: 92,
        weakPoints: <String>[],
        recommendedAction: '保持当前节奏。',
      ),
      LearningAssetMastery(
        assetId: 'asset_sentence',
        materialId: 'material_1',
        materialTitle: 'Run, Hop, Go!',
        text: 'A rabbit can hop fast.',
        kind: 'sentence',
        translation: '兔子能跳得很快。',
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
