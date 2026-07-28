import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:learning_english_contracts/contracts.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/phonics/data/phonics_providers.dart';
import 'package:learning_english_mobile/features/phonics/presentation/widgets/phonics_letter_tile.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';
import 'package:learning_english_mobile/main.dart' as app;

/// Drives the new 自然拼读 (phonics) journey on a simulator and captures one
/// screenshot per screen against a real backend.
///
/// The backend base URL comes from `--dart-define=API_BASE_URL=...`; point it at
/// the seeded local stack:
///   --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
///
/// For a clean first-run flow (login + binding + no-child) erase the simulator
/// first so the stub WeChat device code in the keychain is regenerated:
///   xcrun simctl erase SIM_ID
const String kUnitId = 'phonics_l1_u1';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('phonics unit-1 walkthrough with real backend', (tester) async {
    // Cosmetic overflow / disposed-widget lookups during transitions are still
    // captured in the screenshot and must not fail the harness; everything else
    // propagates and the flow fails loudly via waitFor()/step().
    final defaultOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      final text = details.exceptionAsString();
      if (text.contains('overflowed') || text.contains('deactivated widget')) {
        debugPrint('IGNORED rendering artifact: ${text.split('\n').first}');
        return;
      }
      defaultOnError?.call(details);
    };

    final shots = <String>[];
    Future<void> shot(String name) async {
      await tester.pumpAndSettle(const Duration(milliseconds: 300));
      await binding.takeScreenshot(name);
      shots.add(name);
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

    Future<Finder> waitFor(Finder f,
            {Duration timeout = const Duration(seconds: 25)}) =>
        waitForAny(<Finder>[f], timeout: timeout);

    Future<void> step(String name, Future<void> Function() body) async {
      try {
        await body();
      } catch (e) {
        debugPrint('STEP "$name" failed: $e');
        try {
          await binding.takeScreenshot('ERROR-$name');
        } catch (_) {}
        rethrow;
      }
    }

    // Bottom buttons live at the end of lazy ListViews, so they may not be built
    // until scrolled into view. Scroll the primary scrollable until the label
    // exists, then tap it.
    Future<void> tapText(String label) async {
      final f = find.text(label);
      if (f.evaluate().isEmpty) {
        try {
          await tester.scrollUntilVisible(
            f,
            250,
            scrollable: find.byType(Scrollable).first,
            maxScrolls: 40,
          );
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

    final container =
        ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));

    // Force a clean signed-out start (keychain survives app reinstall).
    final bootEnd = DateTime.now().add(const Duration(seconds: 35));
    while (DateTime.now().isBefore(bootEnd) &&
        container.read(sessionControllerProvider).stage ==
            SessionStage.bootstrapping) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    await container.read(sessionControllerProvider.notifier).clearSession();
    await tester.pumpAndSettle(const Duration(seconds: 2));

    await step('p01-login', () async {
      await waitFor(find.text('微信登录'));
      await shot('p01-login');
      await tester.tap(find.text('微信登录'));
    });

    await step('p02-phone-binding', () async {
      // A previously-bound parent logs straight in, so the binding screen may be
      // skipped; only drive binding when it actually appears.
      await tester.pumpAndSettle(const Duration(seconds: 1));
      if (find.text('获取验证码').evaluate().isNotEmpty) {
        await shot('p02-phone-binding');
        final notifier = container.read(sessionControllerProvider.notifier);
        const phone = '13800138000';
        final otp = await notifier.requestOtp(phone);
        await notifier.bindPhone(phoneNumber: phone, otpCode: otp ?? '123456');
        await tester.pumpAndSettle(const Duration(seconds: 2));
      }
    });

    await step('p03-create-child', () async {
      // Seed a grade-3 child through the authenticated repository (the native
      // profile form is exercised by the main walkthrough).
      final repo = container.read(appRepositoryProvider);
      final child = await repo.createChild(
        name: '小和',
        age: 8,
        level: 'grade3',
        learningGoal: '跟上三年级自然拼读',
        preferredReviewDurationMinutes: 10,
        parentNotes: '二升三，学 PEP 三上',
      );
      await container.read(sessionControllerProvider.notifier).addChild(child);
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('p04-unit-list', () async {
      container.read(appRouterProvider).go('/phonics');
      // Unit card shows the unit code; wait for the seeded L1-U1 unit.
      await waitFor(find.text('L1-U1'), timeout: const Duration(seconds: 20));
      await shot('p04-unit-list');
      // Scroll to the L2 units at the bottom for a second shot, then back up.
      try {
        await tester.scrollUntilVisible(
          find.text('L2-U6'),
          400,
          scrollable: find.byType(Scrollable).first,
          maxScrolls: 40,
        );
        await tester.pumpAndSettle(const Duration(milliseconds: 300));
        await shot('p04b-unit-list-l2');
        await tester.scrollUntilVisible(
          find.text('L1-U1'),
          -400,
          scrollable: find.byType(Scrollable).first,
          maxScrolls: 40,
        );
        await tester.pumpAndSettle(const Duration(milliseconds: 300));
      } catch (_) {}
      // Tapping the (unlocked) card pushes the lesson route.
      await tester.tap(find.text('L1-U1'));
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('p05-sound-intro', () async {
      // Step 1/6: 听音识音 — sound cards + a 继续 button.
      await waitFor(find.text('第 1 步 / 共 6 步'),
          timeout: const Duration(seconds: 20));
      await shot('p05-sound-intro');
      await tapText('继续');
    });

    await step('p06-first-sound', () async {
      // Step 2/4: 圈首音 — tap the correct first-sound letter for each word.
      await waitFor(find.text('它的第一个音是哪个字母？'),
          timeout: const Duration(seconds: 20));
      await shot('p06-first-sound');

      final detail =
          container.read(phonicsUnitProvider(kUnitId)).valueOrNull;
      if (detail == null) {
        throw StateError('phonics unit detail not loaded');
      }
      // Resolve the answers in the exact order the UI presents the items
      // (step.itemIds), so each tap picks the right tile.
      final answerById = <String, String>{
        for (final item in detail.firstSoundItems) item.id: item.answer,
      };
      final fsStep = detail.steps.firstWhere(
        (s) => s.practiceType == PhonicsPracticeType.firstSoundTap,
      );
      final answers = <String>[
        for (final id in fsStep.itemIds)
          if (answerById[id] != null) answerById[id]!,
      ];

      for (var i = 0; i < answers.length; i++) {
        final answer = answers[i];
        final tile = find.widgetWithText(PhonicsLetterTile, answer);
        await waitFor(tile, timeout: const Duration(seconds: 10));
        await tester.ensureVisible(tile.first);
        await tester.pumpAndSettle(const Duration(milliseconds: 200));
        await tester.tap(tile.first);
        await tester.pumpAndSettle(const Duration(milliseconds: 600));
        // Correct tap locks the item and reveals 继续 / 看看结果.
        final isLast = i == answers.length - 1;
        await tapText(isLast ? '看看结果' : '继续');
      }
    });

    await step('p07-first-sound-result', () async {
      // Live-scored result card (圈首音正确率 100%).
      await waitFor(find.text('圈首音完成'), timeout: const Duration(seconds: 15));
      await shot('p07-first-sound-result');
      await tapText('继续');
    });

    await step('p08-blending', () async {
      // Step 3/6: 拼读 — mic + letter tiles. Recording needs a real mic, so we
      // capture the stage and skip the words to reach the next step. The submit/
      // skip buttons sit below the mic (off-screen in the lazy ListView), so wait
      // on the visible step header and let tapText scroll to the buttons.
      await waitFor(find.text('第 3 步 / 共 6 步'),
          timeout: const Duration(seconds: 20));
      await shot('p08-blending');
      for (var i = 0; i < 8; i++) {
        try {
          await tapText('跳过这个词');
        } catch (_) {
          // Last word shows 跳过并完成 instead.
          await tapText('跳过并完成');
          break;
        }
      }
    });

    // Drives a tap-to-assemble stage (tile-build or dictation): reads the step's
    // words from the loaded detail and taps each segment tile in order. Placed
    // tiles move out of the bank and the answer row renders before the bank, so
    // the LAST tile matching a segment is always a bank tile.
    Future<void> driveAssembleStage({
      required String stepKey,
      required String stepHeader,
      required String resultTitle,
      required String shotName,
    }) async {
      await waitFor(find.text(stepHeader), timeout: const Duration(seconds: 20));
      await shot(shotName);
      final detail = container.read(phonicsUnitProvider(kUnitId)).valueOrNull;
      if (detail == null) {
        throw StateError('phonics unit detail not loaded');
      }
      final lessonStep = detail.steps.firstWhere((s) => s.key == stepKey);
      final byId = <String, PhonicsDecodableWord>{
        for (final w in detail.decodableWords) w.id: w,
      };
      final words = <PhonicsDecodableWord>[
        for (final id in lessonStep.wordIds)
          if (byId[id] != null) byId[id]!,
      ];
      for (var wi = 0; wi < words.length; wi++) {
        for (final seg in words[wi].segments) {
          final tile = find.widgetWithText(PhonicsLetterTile, seg);
          await waitFor(tile, timeout: const Duration(seconds: 10));
          await tester.ensureVisible(tile.last);
          await tester.pumpAndSettle(const Duration(milliseconds: 150));
          await tester.tap(tile.last);
          await tester.pumpAndSettle(const Duration(milliseconds: 300));
        }
        final isLast = wi == words.length - 1;
        await tapText(isLast ? '看看结果' : '继续');
      }
      await waitFor(find.text(resultTitle), timeout: const Duration(seconds: 15));
      await tapText('继续');
    }

    await step('p08b-tile-build', () async {
      // Step 4/6: 搭词 — arrange scrambled tiles into the target word.
      await driveAssembleStage(
        stepKey: 'tile_build',
        stepHeader: '第 4 步 / 共 6 步',
        resultTitle: '搭词完成',
        shotName: 'p08b-tile-build',
      );
    });

    await step('p08c-dictation', () async {
      // Step 5/6: 听写 — spell the heard word from tiles (word hidden).
      await driveAssembleStage(
        stepKey: 'dictation',
        stepHeader: '第 5 步 / 共 6 步',
        resultTitle: '听写完成',
        shotName: 'p08c-dictation',
      );
    });

    await step('p09-heart-word', () async {
      // Step 6/6: 高频词 (heart words). The 完成这一课 button is below the cards,
      // so wait on the visible step header and scroll to the button.
      await waitFor(find.text('第 6 步 / 共 6 步'),
          timeout: const Duration(seconds: 20));
      await shot('p09-heart-word');
      await tapText('完成这一课');
    });

    await step('p10-completion', () async {
      // Completion hero + 学习成果 stats. Wait on the celebratory eyebrow (top of
      // the hero card) which is always visible.
      await waitFor(find.text('完成啦'), timeout: const Duration(seconds: 15));
      await shot('p10-completion');
      // Scroll to reveal the 学习成果 stats card for a second, richer shot.
      try {
        await tester.scrollUntilVisible(
          find.text('学习成果'),
          250,
          scrollable: find.byType(Scrollable).first,
          maxScrolls: 10,
        );
        await tester.pumpAndSettle(const Duration(milliseconds: 300));
        await shot('p11-learning-outcomes');
      } catch (_) {}
    });

    debugPrint('PHONICS WALKTHROUGH screenshots: ${shots.join(", ")}');
  }, timeout: const Timeout(Duration(minutes: 8)));
}
