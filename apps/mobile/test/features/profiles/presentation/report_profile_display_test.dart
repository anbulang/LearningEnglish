import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_mobile/core/theme/app_theme.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/profiles/presentation/profile_screen.dart';
import 'package:learning_english_mobile/features/review/presentation/review_tasks_screen.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';

void main() {
  testWidgets('报告页没有孩子档案时显示可操作空状态', (tester) async {
    await _pumpScreen(
      tester,
      const ReviewTasksScreen(reportMode: true),
      overrides: <Override>[
        activeChildProvider.overrideWithValue(null),
      ],
    );

    expect(find.text('先添加孩子档案'), findsOneWidget);
    expect(find.text('报告加载失败'), findsNothing);
    expect(find.text('去我的页面添加'), findsOneWidget);
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
