import 'dart:async';
import 'dart:convert';
import 'dart:io';

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
import 'package:learning_english_mobile/features/speaking/data/speaking_recorder_controller.dart';
import 'package:learning_english_mobile/main.dart' as app;

import 'phonics_ship_audio.dart';

/// Real DashScope ASR on the simulator, end-to-end through the actual app UI.
///
/// The simulator has no microphone, so we open the L2 digraph unit directly and
/// inject a *real* TTS render of "ship" as the recording, then submit it through
/// the app's genuine upload → DashScope ASR → scoring path and capture the real
/// transcript rendered in the UI. Point the app at the live real-provider
/// backend: --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
const String kUnitId = 'phonics_l2_u1';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('real DashScope ASR for an L2 digraph word (ship)', (tester) async {
    final defaultOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      final text = details.exceptionAsString();
      if (text.contains('overflowed') || text.contains('deactivated widget')) {
        return;
      }
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

    // login + phone binding
    await waitFor(find.text('微信登录'));
    await tester.tap(find.text('微信登录'));
    await tester.pumpAndSettle(const Duration(seconds: 1));
    if (find.text('获取验证码').evaluate().isNotEmpty) {
      final notifier = container.read(sessionControllerProvider.notifier);
      const phone = '13800138000';
      final otp = await notifier.requestOtp(phone);
      await notifier.bindPhone(phoneNumber: phone, otpCode: otp ?? '123456');
      await tester.pumpAndSettle(const Duration(seconds: 2));
    }

    // grade-3 child
    final repo = container.read(appRepositoryProvider);
    final child = await repo.createChild(
      name: '小和', age: 8, level: 'grade3', learningGoal: '拼读',
      preferredReviewDurationMinutes: 10, parentNotes: '',
    );
    await container.read(sessionControllerProvider.notifier).addChild(child);
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Open the L2 digraph unit directly (the lesson route isn't lock-gated; the
    // lock only hides the list tap-target).
    container.read(appRouterProvider).go('/phonics/unit/$kUnitId');

    // Step 1/6 听音识音 — real TTS should be ready (audio buttons, not "生成中").
    await waitFor(find.text('第 1 步 / 共 6 步'), timeout: const Duration(seconds: 20));
    await shot('r01-sound-intro-real-tts');
    await tapText('继续');

    // Step 2/6 圈首音 — tap the digraph first sounds (sh / ch), scored live.
    await waitFor(find.text('它的第一个音是哪个字母？'), timeout: const Duration(seconds: 20));
    final detail = container.read(phonicsUnitProvider(kUnitId)).valueOrNull;
    if (detail == null) {
      throw StateError('unit detail not loaded');
    }
    final answerById = <String, String>{
      for (final i in detail.firstSoundItems) i.id: i.answer,
    };
    final fsStep = detail.steps.firstWhere((s) => s.practiceType == PhonicsPracticeType.firstSoundTap);
    final answers = <String>[for (final id in fsStep.itemIds) if (answerById[id] != null) answerById[id]!];
    for (var i = 0; i < answers.length; i++) {
      final tile = find.widgetWithText(PhonicsLetterTile, answers[i]);
      await waitFor(tile, timeout: const Duration(seconds: 10));
      await tester.ensureVisible(tile.first);
      await tester.pumpAndSettle(const Duration(milliseconds: 200));
      await tester.tap(tile.first);
      await tester.pumpAndSettle(const Duration(milliseconds: 600));
      await tapText(i == answers.length - 1 ? '看看结果' : '继续');
    }
    await waitFor(find.text('圈首音完成'), timeout: const Duration(seconds: 15));
    await tapText('继续');

    // Step 3/6 拼读 — real DashScope ASR on the injected "ship" clip.
    await waitFor(find.text('第 3 步 / 共 6 步'), timeout: const Duration(seconds: 20));
    await shot('r02-blending-real-tts');

    final shipFile = File('${Directory.systemTemp.path}/phonics_ship_probe.mp3');
    shipFile.writeAsBytesSync(base64Decode(kShipAudioB64));
    container
        .read(speakingRecorderControllerProvider.notifier)
        .injectRecording(path: shipFile.path, durationMs: 1200);
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    await tapText('提交给 AI');

    // Real ASR round-trips via DashScope (upload -> worker -> paraformer). Wait
    // for the scored result card rendered in the UI.
    await waitForAny(<Finder>[
      find.textContaining('AI 听到'),
      find.text('读得不错！'),
    ], timeout: const Duration(seconds: 90));
    await tester.pumpAndSettle(const Duration(milliseconds: 400));
    await shot('r03-real-asr-result');

    // Surface the transcript in the run log for the operator.
    final heard = find.textContaining('AI 听到');
    if (heard.evaluate().isNotEmpty) {
      final w = tester.widget<Text>(heard.first);
      debugPrint('REAL ASR RESULT: ${w.data}');
    }
    debugPrint('REAL ASR screenshots: r01-sound-intro-real-tts, r02-blending-real-tts, r03-real-asr-result');
  }, timeout: const Timeout(Duration(minutes: 8)));
}
