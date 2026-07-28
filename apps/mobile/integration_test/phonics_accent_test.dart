import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/session/data/session_controller.dart';
import 'package:learning_english_mobile/features/session/data/session_models.dart';
import 'package:learning_english_mobile/main.dart' as app;

/// Per-child 美音/英音 accent switch, end-to-end against the live real backend.
/// Flips the toggle in the profile screen and asserts the phonics audio the API
/// serves for this child switches from the -us render to the -uk render.
///   --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
const String kUnitId = 'phonics_l2_u1';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('per-child accent toggle switches served audio (us <-> uk)', (tester) async {
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

    Future<Finder> waitFor(Finder f, {Duration timeout = const Duration(seconds: 25)}) async {
      final end = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(end)) {
        await tester.pump(const Duration(milliseconds: 400));
        if (f.evaluate().isNotEmpty) return f;
      }
      throw TimeoutException('$f did not appear within $timeout');
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
      name: '小和', age: 8, level: 'grade3', learningGoal: '拼读',
      preferredReviewDurationMinutes: 10, parentNotes: '',
    );
    await container.read(sessionControllerProvider.notifier).addChild(child);
    await tester.pumpAndSettle(const Duration(seconds: 1));

    Future<String> servedSoundUrl() async {
      final detail = await repo.getPhonicsUnit(kUnitId, child.id);
      final card = detail.soundCards.firstWhere((c) => c.id == 'card_sh');
      return card.soundAudioUrl;
    }

    // default us
    container.read(appRouterProvider).go('/profile');
    await waitFor(find.text('美音'), timeout: const Duration(seconds: 20));
    await tester.ensureVisible(find.text('英音'));
    await shot('a01-accent-us');
    final usUrl = await servedSoundUrl();
    debugPrint('ACCENT us url: $usUrl');
    expect(usUrl.contains('-us'), isTrue, reason: usUrl);

    // switch to 英音
    await tester.tap(find.text('英音'));
    await tester.pumpAndSettle(const Duration(seconds: 3));
    await shot('a02-accent-uk');
    final ukUrl = await servedSoundUrl();
    debugPrint('ACCENT uk url: $ukUrl');
    expect(ukUrl.contains('-uk'), isTrue, reason: ukUrl);
    expect(usUrl == ukUrl, isFalse);

    debugPrint('ACCENT toggle screenshots: a01-accent-us, a02-accent-uk');
  }, timeout: const Timeout(Duration(minutes: 8)));
}
