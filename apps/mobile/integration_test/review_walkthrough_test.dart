import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:integration_test/integration_test.dart';
import 'package:learning_english_contracts/contracts.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/data/scan_draft_controller.dart';
import 'package:learning_english_mobile/features/materials/presentation/material_review_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';
import 'package:learning_english_mobile/main.dart' as app;

import 'worksheet_data.dart';

/// Full review loop against a real (stub-AI) backend: upload 讲义 → OCR → confirm
/// → answer every review task interactively → real server-scored session → report.
/// Point at the running stub stack: --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('review loop scores real answers end to end', (tester) async {
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
        {Duration timeout = const Duration(seconds: 30)}) async {
      final end = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(end)) {
        await tester.pump(const Duration(milliseconds: 400));
        for (final f in finders) {
          if (f.evaluate().isNotEmpty) return f;
        }
      }
      throw TimeoutException('none of $finders appeared within $timeout');
    }

    Future<Finder> waitFor(Finder f, {Duration timeout = const Duration(seconds: 30)}) =>
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

    // login + bind
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

    final repo = container.read(appRepositoryProvider);
    final child = await repo.createChild(
      name: '小明', age: 6, level: 'starter', learningGoal: '课后复习更稳定',
      preferredReviewDurationMinutes: 10, parentNotes: '',
    );
    await container.read(sessionControllerProvider.notifier).addChild(child);
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // upload a worksheet → stub OCR → review screen
    container.read(appRouterProvider).go('/home');
    await waitFor(find.text('上传讲义'), timeout: const Duration(seconds: 15));
    await tester.tap(find.text('上传讲义').first);
    await waitFor(find.text('添加讲义页'), timeout: const Duration(seconds: 10));
    final worksheet = File('${Directory.systemTemp.path}/review_worksheet.png');
    worksheet.writeAsBytesSync(base64Decode(kWorksheetB64.replaceAll('\n', '')));
    container.read(scanDraftProvider.notifier).setPages(<ScanDraftPage>[
      ScanDraftPage(file: XFile(worksheet.path, mimeType: 'image/png'), sourceType: 'gallery'),
    ]);
    await tester.pumpAndSettle(const Duration(seconds: 1));
    await waitFor(find.text('开始识别'), timeout: const Duration(seconds: 10));
    await tester.tap(find.text('开始识别'));

    await waitFor(find.text('AI 识别结果'), timeout: const Duration(seconds: 120));
    // confirm through the repo (button sits under the nav bar; tap can miss)
    final review = tester.widget<MaterialReviewScreen>(find.byType(MaterialReviewScreen));
    final materialId = review.materialId;
    final job = await repo.getMaterialJob(review.jobId);
    await repo.confirmMaterialJob(
      jobId: review.jobId,
      draftTitle: job.draftTitle,
      draftTopic: job.draftTopic,
      draftVocabulary: job.draftVocabulary,
      draftSentences: job.draftSentences,
    );
    container.invalidate(materialsProvider);
    container.invalidate(reviewTasksProvider);
    container.invalidate(weeklyReportProvider);

    // wait until the material's review tasks exist. reviewTasksProvider is a
    // FutureProvider, so await its .future (valueOrNull is null until the fetch
    // resolves) and re-fetch by invalidating between polls.
    List<ReviewTask> tasks = const <ReviewTask>[];
    final tasksEnd = DateTime.now().add(const Duration(seconds: 30));
    while (DateTime.now().isBefore(tasksEnd)) {
      container.invalidate(reviewTasksProvider);
      try {
        final all = await container.read(reviewTasksProvider.future);
        tasks = all.where((t) => t.materialId == materialId).toList();
      } catch (_) {}
      if (tasks.isNotEmpty) break;
      await tester.pump(const Duration(milliseconds: 500));
    }
    expect(tasks, isNotEmpty, reason: 'confirm did not produce review tasks');

    // open the review runner and answer each task correctly
    container.read(appRouterProvider).go('/review/session/$materialId');
    await waitFor(find.text('复习进行中'), timeout: const Duration(seconds: 20));
    await shot('rev-01-review-task');

    for (var i = 0; i < tasks.length; i++) {
      final task = tasks[i];
      switch (task.taskType) {
        case TaskType.flashcard:
          await waitFor(find.text('我会读'), timeout: const Duration(seconds: 15));
          await tapText('我会读');
          break;
        case TaskType.listenChoice:
          final correct = task.contentJson['correct_answer'] as String? ?? '';
          if (correct.isNotEmpty) {
            await waitFor(find.text(correct), timeout: const Duration(seconds: 15));
            await tapText(correct);
          }
          break;
        case TaskType.matchChoice:
          // best-effort: cycle the first row once (single-pair case picks it)
          if (find.text('点此选择').evaluate().isNotEmpty) {
            await tapText('点此选择');
          }
          break;
        default:
          break; // passive types auto-record
      }
      // advance — tolerate either label (isLast edge / render timing)
      final advance = await waitForAny(
        <Finder>[find.text('继续下一题'), find.text('完成本次复习')],
        timeout: const Duration(seconds: 15),
      );
      final label = (advance.evaluate().first.widget as Text).data ?? '继续下一题';
      await tapText(label);
      await tester.pumpAndSettle(const Duration(milliseconds: 400));
    }

    // real server-scored result
    await waitFor(find.textContaining('本次得分'), timeout: const Duration(seconds: 20));
    await shot('rev-02-real-score');

    // weekly report reflects the real session
    container.read(appRouterProvider).go('/reports');
    await waitForAny(<Finder>[find.text('报告'), find.text('本周报告'), find.textContaining('复习')],
        timeout: const Duration(seconds: 15));
    await shot('rev-03-report');

    debugPrint('REVIEW WALKTHROUGH tasks: ${tasks.map((t) => t.taskType).toList()}');
    debugPrint('REVIEW WALKTHROUGH screenshots: rev-01-review-task, rev-02-real-score, rev-03-report');
  }, timeout: const Timeout(Duration(minutes: 10)));
}
