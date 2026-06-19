import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:integration_test/integration_test.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/data/scan_draft_controller.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_review_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';
import 'package:learning_english_mobile/main.dart' as app;

import 'worksheet_data.dart';

/// Drives the full parent journey on a simulator and captures one screenshot
/// per screen against a real backend.
///
/// The backend base URL comes from `--dart-define=API_BASE_URL=...` (the app's
/// `ApiClient.defaultBaseUrl`); point it at the harness stack:
///   --dart-define=API_BASE_URL=http://127.0.0.1:8010/v1
///
/// For a clean first-run flow (login + binding + no-child) erase the simulator
/// first. The stub WeChat device code (a random `mobile-wechat-parent-...`) is
/// stored in the simulator keychain, which survives an app uninstall; erasing
/// the device wipes it so the next run generates a new code and the backend
/// returns a fresh, unbound parent that still needs phone binding:
///   xcrun simctl erase SIM_ID
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('full family walkthrough with real backend', (tester) async {
    // A RenderFlex overflow (or the disposed-widget lookup it triggers during a
    // transition) is a cosmetic layout issue that is still captured in the
    // screenshot; it must not fail this flow harness. Every other error still
    // propagates, and the flow itself fails loudly via waitFor()/step() below.
    final defaultOnError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      final text = details.exceptionAsString();
      if (text.contains('overflowed') ||
          text.contains('deactivated widget')) {
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

    // Pumps until one of [finders] has a match and returns it. Throws on
    // timeout so a missing screen fails the harness loudly instead of silently
    // capturing the wrong screen under an expected name.
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

    // Captures a diagnostic screenshot and rethrows, so any unexpected failure
    // in a step fails the test rather than leaving a green run with missing or
    // wrong screenshots.
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

    await app.main();
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await binding.convertFlutterSurfaceToImage();
    await tester.pumpAndSettle();

    final container =
        ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    // The simulator keychain survives an app uninstall, so a previous run's
    // token would auto-authenticate and skip the login/binding screens. Force a
    // clean signed-out start. (The backend base URL comes from --dart-define.)
    //
    // Wait for the startup bootstrap to settle first: if a refresh is still in
    // flight, clearSession() could be undone when bootstrap() later persists the
    // refreshed session, and the login/binding screens would be skipped anyway.
    // The Dio client uses 30s timeouts, so allow the refresh to finish before
    // giving up.
    final bootEnd = DateTime.now().add(const Duration(seconds: 35));
    while (DateTime.now().isBefore(bootEnd) &&
        container.read(sessionControllerProvider).stage ==
            SessionStage.bootstrapping) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    expect(
        container.read(sessionControllerProvider).stage ==
            SessionStage.bootstrapping,
        isFalse,
        reason: 'bootstrap did not finish before clearing the session');
    await container.read(sessionControllerProvider.notifier).clearSession();
    await tester.pumpAndSettle(const Duration(seconds: 2));

    await step('01-login', () async {
      await waitFor(find.text('微信登录'));
      await shot('01-login');
      await tester.tap(find.text('微信登录'));
    });

    await step('02-phone-binding', () async {
      await waitFor(find.text('获取验证码'));
      await shot('02-phone-binding');
      // The native form needs a phone number plus the server debug OTP; drive it
      // through the controller for determinism. requestOtp returns the debug
      // code in non-prod mode.
      final notifier = container.read(sessionControllerProvider.notifier);
      const phone = '13800138000';
      final otp = await notifier.requestOtp(phone);
      await notifier.bindPhone(phoneNumber: phone, otpCode: otp ?? '123456');
      await tester.pumpAndSettle(const Duration(seconds: 2));
    });

    await step('03-home-no-child', () async {
      // The no-child empty-state copy differs across app versions; accept either.
      await waitForAny(<Finder>[
        find.text('先添加孩子档案'),
        find.text('还没有孩子档案'),
      ]);
      await shot('03-home-no-child');
    });

    await step('04-profile', () async {
      // Open the profile screen for the screenshot, then seed the child via the
      // authenticated repository instead of driving the native form.
      container.read(appRouterProvider).go('/profile');
      await tester.pumpAndSettle(const Duration(seconds: 1));
      await shot('04-profile');
      final repo = container.read(appRepositoryProvider);
      final child = await repo.createChild(
        name: '小明',
        age: 6,
        level: 'starter',
        learningGoal: '课后复习更稳定',
        preferredReviewDurationMinutes: 10,
        parentNotes: '',
      );
      await container.read(sessionControllerProvider.notifier).addChild(child);
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('05-home-with-child', () async {
      container.read(appRouterProvider).go('/home');
      await waitFor(find.text('上传讲义'), timeout: const Duration(seconds: 15));
      await shot('05-home-with-child');
      await tester.tap(find.text('上传讲义').first);
    });

    await step('06-scan-ready', () async {
      // The scan screen shows '添加讲义页' before any page is added; the submit
      // button only becomes '开始识别' once a page exists (it reads '先添加讲义页'
      // while empty), so wait for the screen first, then add the page.
      await waitFor(find.text('添加讲义页'), timeout: const Duration(seconds: 10));
      final bytes = base64Decode(kWorksheetB64.replaceAll('\n', ''));
      // The repository uploads via MultipartFile.fromFile(page.file.path), so the
      // page must be backed by a real file on disk — an in-memory XFile.fromData
      // exposes no path and the upload fails before reaching the API.
      final worksheetFile =
          File('${Directory.systemTemp.path}/walkthrough_worksheet.png');
      worksheetFile.writeAsBytesSync(bytes);
      container.read(scanDraftProvider.notifier).setPages(<ScanDraftPage>[
        ScanDraftPage(
          file: XFile(worksheetFile.path, mimeType: 'image/png'),
          sourceType: 'gallery',
        ),
      ]);
      await tester.pumpAndSettle(const Duration(seconds: 1));
      await waitFor(find.text('开始识别'), timeout: const Duration(seconds: 10));
      await shot('06-scan-ready');
      await tester.tap(find.text('开始识别'));
    });

    await step('07-review-editable', () async {
      // Real qwen OCR runs server-side, then the review screen appears. Allow
      // at least the backend's AI_REQUEST_TIMEOUT_SECONDS (default 180s) plus
      // queue/startup overhead so a healthy-but-slow OCR run doesn't fail here
      // before the worker would.
      await waitFor(find.text('AI 识别结果'),
          timeout: const Duration(seconds: 220));
      await shot('07-review-editable');
      // Showcase editable proof-reading: delete a word chip if present (optional).
      final dog = find.descendant(
        of: find.widgetWithText(InputChip, 'dog'),
        matching: find.byIcon(Icons.close_rounded),
      );
      if (dog.evaluate().isNotEmpty) {
        await tester.tap(dog.first, warnIfMissed: false);
        await tester.pumpAndSettle();
        await shot('07b-review-after-edit');
      }
    });

    var lessonMaterialId = '';
    await step('08-confirm-to-lesson', () async {
      // The confirm button sits at the bottom under the nav bar and the tap can
      // miss; confirm through the repository using the ids the review screen
      // already holds, then navigate to the generated lesson.
      final review = tester
          .widget<MaterialReviewScreen>(find.byType(MaterialReviewScreen));
      lessonMaterialId = review.materialId;
      final repo = container.read(appRepositoryProvider);
      final job = await repo.getMaterialJob(review.jobId);
      await repo.confirmMaterialJob(
        jobId: review.jobId,
        draftTitle: job.draftTitle,
        draftTopic: job.draftTopic,
        draftVocabulary: job.draftVocabulary,
        draftSentences: job.draftSentences,
      );
      // MaterialReviewScreen._confirm invalidates these after a UI confirm;
      // the direct repository call skips that, so the data Home/lesson/review/
      // report screens cached as empty before upload would stay stale (e.g. the
      // review runner showing "no tasks"). Refresh them here too.
      container.invalidate(materialProvider(lessonMaterialId));
      container.invalidate(knowledgePackProvider(lessonMaterialId));
      container.invalidate(parentCoachingScriptProvider(lessonMaterialId));
      container.invalidate(materialsProvider);
      container.invalidate(reviewTasksProvider);
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await waitFor(find.text('课程详情'), timeout: const Duration(seconds: 25));
      await shot('08-lesson-detail');
    });

    await step('09-lesson-media', () async {
      // Still on the lesson detail; let DashScope media generation progress.
      // Full readiness can take minutes and is verified separately by
      // lesson_media_ready_test, so this only captures the in-progress state.
      await waitFor(find.text('课程详情'), timeout: const Duration(seconds: 10));
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(seconds: 2));
      }
      await shot('09-lesson-media');
    });

    await step('11-speaking', () async {
      // Navigate via the router (lesson-detail action buttons sit at the bottom
      // and the tap can miss); the captured screen is identical either way.
      container.read(appRouterProvider).go('/review/speaking/$lessonMaterialId');
      await waitFor(find.text('口语陪练'), timeout: const Duration(seconds: 15));
      await shot('11-speaking');
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('12-review-runner', () async {
      container.read(appRouterProvider).go('/review/session/$lessonMaterialId');
      await waitFor(find.text('复习进行中'), timeout: const Duration(seconds: 15));
      await shot('12-review-runner');
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('13-reports', () async {
      await waitFor(find.text('报告'), timeout: const Duration(seconds: 10));
      await tester.tap(find.text('报告').last);
      await tester.pumpAndSettle(const Duration(seconds: 2));
      await shot('13-reports');
    });

    // Emit the material id so the operator can feed it straight into
    // lesson_media_ready_test (--dart-define=MATERIAL_ID=...).
    debugPrint('WALKTHROUGH material_id: $lessonMaterialId');
    debugPrint('WALKTHROUGH screenshots: ${shots.join(", ")}');
  }, timeout: const Timeout(Duration(minutes: 12)));
}
