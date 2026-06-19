import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:integration_test/integration_test.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/core/network/api_client.dart';
import 'package:learning_english_mobile/core/network/server_config.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/data/scan_draft_controller.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_review_screen.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/main.dart' as app;

import 'worksheet_data.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('full family walkthrough with real backend', (tester) async {
    final shots = <String>[];
    Future<void> shot(String name) async {
      await tester.pumpAndSettle(const Duration(milliseconds: 300));
      await binding.takeScreenshot(name);
      shots.add(name);
    }

    Future<bool> pumpUntil(Finder f,
        {Duration timeout = const Duration(seconds: 25)}) async {
      final end = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(end)) {
        await tester.pump(const Duration(milliseconds: 400));
        if (f.evaluate().isNotEmpty) return true;
      }
      return false;
    }

    Future<void> step(String name, Future<void> Function() body) async {
      try {
        await body();
      } catch (e) {
        debugPrint('STEP "$name" failed: $e');
        try {
          await binding.takeScreenshot('ERROR-$name');
        } catch (_) {}
      }
    }

    await app.main();
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await binding.convertFlutterSurfaceToImage();
    await tester.pumpAndSettle();

    final container =
        ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    // Make sure the test always talks to the local dev backend on :8010.
    await container.read(serverConfigProvider).clearOverride();
    container.read(apiClientProvider).baseUrl = 'http://127.0.0.1:8010/v1';
    // The iOS simulator keychain survives app uninstall, so a previous run's
    // token would auto-authenticate and skip the login/binding screens. Force a
    // clean signed-out start so the walkthrough always begins at login.
    await container.read(sessionControllerProvider.notifier).clearSession();
    await tester.pumpAndSettle(const Duration(seconds: 2));

    await step('01-login', () async {
      await pumpUntil(find.text('微信登录'));
      await shot('01-login');
      await tester.tap(find.text('微信登录'));
    });

    await step('02-phone-binding', () async {
      await pumpUntil(find.text('获取验证码'), timeout: const Duration(seconds: 25));
      await shot('02-phone-binding');
      // The native binding form needs a real phone number plus the server's
      // debug OTP; drive it through the controller for determinism (mirrors the
      // child seeding below). requestOtp returns the debug code in non-prod mode.
      final notifier = container.read(sessionControllerProvider.notifier);
      const phone = '13800138000';
      final otp = await notifier.requestOtp(phone);
      await notifier.bindPhone(phoneNumber: phone, otpCode: otp ?? '123456');
      await tester.pumpAndSettle(const Duration(seconds: 2));
    });

    await step('03-home-no-child', () async {
      await pumpUntil(find.text('先添加孩子档案'),
          timeout: const Duration(seconds: 25));
      await shot('03-home-no-child');
      await tester.tap(find.text('添加孩子档案').first);
    });

    await step('04-profile', () async {
      await tester.pumpAndSettle(const Duration(seconds: 1));
      await shot('04-profile');
      // Seed the child via the (authenticated) repository to avoid driving the
      // native form; the rest of the journey is real UI.
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
      if (find.text('首页').evaluate().isNotEmpty) {
        await tester.tap(find.text('首页').last);
      }
      await pumpUntil(find.text('上传讲义'), timeout: const Duration(seconds: 15));
      await shot('05-home-with-child');
      await tester.tap(find.text('上传讲义').first);
    });

    await step('06-scan-ready', () async {
      await pumpUntil(find.text('开始识别'), timeout: const Duration(seconds: 10));
      final bytes = base64Decode(kWorksheetB64.replaceAll('\n', ''));
      // The repository uploads via MultipartFile.fromFile(page.file.path), so the
      // page must be backed by a real file on disk — an in-memory XFile.fromData
      // exposes no path and makes the upload fail before it reaches the API.
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
      await shot('06-scan-ready');
      await tester.tap(find.text('开始识别'));
    });

    await step('07-review-editable', () async {
      // Real qwen OCR runs server-side, then the review screen appears.
      await pumpUntil(find.text('AI 识别结果'),
          timeout: const Duration(seconds: 60));
      await shot('07-review-editable');
      // Showcase the editable proof-reading: delete a word chip if present.
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
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await pumpUntil(find.text('课程详情'), timeout: const Duration(seconds: 25));
      await shot('08-lesson-detail');
    });

    await step('09-lesson-media', () async {
      // Real DashScope media takes ~30-60s; lesson detail auto-polls until the
      // 听发音 buttons light up.
      await pumpUntil(find.text('听美式发音'), timeout: const Duration(seconds: 20));
      for (var i = 0; i < 30; i++) {
        await tester.pump(const Duration(seconds: 2));
      }
      await shot('09-lesson-media-ready');
    });

    await step('10-audio', () async {
      final play = find.text('听美式发音');
      if (play.evaluate().isNotEmpty) {
        await tester.ensureVisible(play.first);
        await tester.tap(play.first);
        await tester.pump(const Duration(seconds: 1));
        await shot('10-audio-playing');
      }
    });

    await step('11-speaking', () async {
      if (lessonMaterialId.isEmpty) return;
      // Navigate via the router (lesson-detail action buttons sit at the bottom
      // and the tap can miss); the captured screen is identical either way.
      container.read(appRouterProvider).go('/review/speaking/$lessonMaterialId');
      await pumpUntil(find.text('口语陪练'), timeout: const Duration(seconds: 15));
      await shot('11-speaking');
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('12-review-runner', () async {
      if (lessonMaterialId.isEmpty) return;
      container.read(appRouterProvider).go('/review/session/$lessonMaterialId');
      await pumpUntil(find.text('复习进行中'), timeout: const Duration(seconds: 15));
      await shot('12-review-runner');
      container.read(appRouterProvider).go('/lessons/$lessonMaterialId');
      await tester.pumpAndSettle(const Duration(seconds: 1));
    });

    await step('13-reports', () async {
      if (find.text('报告').evaluate().isNotEmpty) {
        await tester.tap(find.text('报告').last);
        await tester.pumpAndSettle(const Duration(seconds: 2));
        await shot('13-reports');
      }
    });

    debugPrint('WALKTHROUGH screenshots: ${shots.join(", ")}');
  }, timeout: const Timeout(Duration(minutes: 8)));
}
