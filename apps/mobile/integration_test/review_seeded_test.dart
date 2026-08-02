import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:learning_english_contracts/contracts.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';
import 'package:learning_english_mobile/main.dart' as app;

/// Deterministic review-loop screenshot, bypassing the flaky local OCR enqueue.
/// Phase A (no SEED_MATERIAL_ID): create a child under the sim's account, print
/// its id so a script can seed tasks for it. Phase B (SEED_MATERIAL_ID set): log
/// back in (same account, do NOT erase between phases) and drive the review of
/// the seeded material — real server scoring → real weekly report.
const String kSeedMaterialId = String.fromEnvironment('SEED_MATERIAL_ID', defaultValue: '');

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('seeded review loop', (tester) async {
    final defaultOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      final text = details.exceptionAsString();
      if (text.contains('overflowed') || text.contains('deactivated widget')) return;
      defaultOnError?.call(details);
    };

    Future<void> shot(String name) async {
      await tester.pumpAndSettle(const Duration(milliseconds: 300));
      await binding.takeScreenshot(name);
    }

    Future<Finder> waitForAny(List<Finder> finders,
        {Duration timeout = const Duration(seconds: 25)}) async {
      final end = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(end)) {
        await tester.pump(const Duration(milliseconds: 400));
        for (final f in finders) {
          if (f.evaluate().isNotEmpty) return f;
        }
      }
      throw TimeoutException('none of $finders appeared within $timeout');
    }

    Future<Finder> waitFor(Finder f, {Duration timeout = const Duration(seconds: 25)}) =>
        waitForAny(<Finder>[f], timeout: timeout);

    Future<void> tapText(String label) async {
      final f = find.text(label);
      if (f.evaluate().isEmpty) {
        try {
          await tester.scrollUntilVisible(f, 250,
              scrollable: find.byType(Scrollable).first, maxScrolls: 40);
        } catch (_) {}
      }
      await tester.ensureVisible(f.first);
      await tester.pumpAndSettle(const Duration(milliseconds: 300));
      await tester.tap(f.first, warnIfMissed: false);
      await tester.pumpAndSettle(const Duration(seconds: 1));
    }

    await app.main();
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await binding.convertFlutterSurfaceToImage();
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    final bootEnd = DateTime.now().add(const Duration(seconds: 35));
    while (DateTime.now().isBefore(bootEnd) &&
        container.read(sessionControllerProvider).stage == SessionStage.bootstrapping) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    await container.read(sessionControllerProvider.notifier).clearSession();
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // login (+ bind if first time on this account)
    await waitFor(find.text('微信登录'));
    await tester.tap(find.text('微信登录'));
    await tester.pumpAndSettle(const Duration(seconds: 1));
    if (find.text('获取验证码').evaluate().isNotEmpty) {
      final n = container.read(sessionControllerProvider.notifier);
      final otp = await n.requestOtp('13800138000');
      await n.bindPhone(phoneNumber: '13800138000', otpCode: otp ?? '123456');
      await tester.pumpAndSettle(const Duration(seconds: 2));
    }

    final repo = container.read(appRepositoryProvider);

    if (kSeedMaterialId.isEmpty) {
      // Phase A: ensure exactly one child exists, print its id for seeding.
      var child = container.read(activeChildProvider);
      child ??= await () async {
        final c = await repo.createChild(
          name: '小明', age: 6, level: 'starter', learningGoal: '课后复习',
          preferredReviewDurationMinutes: 10, parentNotes: '',
        );
        await container.read(sessionControllerProvider.notifier).addChild(c);
        return c;
      }();
      await tester.pumpAndSettle(const Duration(seconds: 1));
      debugPrint('REVIEW_CHILD_ID:${child.id}');
      return;
    }

    // Phase B: drive the seeded material's review.
    await waitForAny(<Finder>[find.text('上传讲义'), find.text('自然拼读')],
        timeout: const Duration(seconds: 15)); // home is up
    final tasks = (await container.read(reviewTasksProvider.future))
        .where((t) => t.materialId == kSeedMaterialId)
        .toList();
    expect(tasks, isNotEmpty, reason: 'seeded review tasks missing for $kSeedMaterialId');

    container.read(appRouterProvider).go('/review/session/$kSeedMaterialId');
    await waitFor(find.text('复习进行中'), timeout: const Duration(seconds: 20));
    await shot('rv-01-review-task');

    for (var i = 0; i < tasks.length; i++) {
      final task = tasks[i];
      if (task.taskType == TaskType.flashcard) {
        // self-rate 还不熟 → an honest miss, so the score isn't a trivial 100 and
        // the word surfaces as a weak point in the report.
        await waitFor(find.text('还不熟'));
        if (i == 0) await shot('rv-02b-flashcard');
        await tapText('还不熟');
      } else if (task.taskType == TaskType.listenChoice) {
        final correct = task.contentJson['correct_answer'] as String? ?? '';
        if (correct.isNotEmpty) {
          await waitFor(find.text(correct));
          if (i == 0) await shot('rv-02-listen-choice');
          await tapText(correct);
        }
      }
      final advance = await waitForAny(
        <Finder>[find.text('继续下一题'), find.text('完成本次复习')],
        timeout: const Duration(seconds: 15),
      );
      await tapText((advance.evaluate().first.widget as Text).data ?? '继续下一题');
      await tester.pumpAndSettle(const Duration(milliseconds: 400));
    }

    await waitFor(find.textContaining('本次得分'), timeout: const Duration(seconds: 20));
    await shot('rv-03-real-score');

    container.read(appRouterProvider).go('/reports');
    await waitForAny(<Finder>[find.text('报告'), find.textContaining('复习'), find.textContaining('薄弱')],
        timeout: const Duration(seconds: 15));
    await shot('rv-04-report');
    debugPrint('SEEDED REVIEW screenshots done');
  }, timeout: const Timeout(Duration(minutes: 6)));
}
