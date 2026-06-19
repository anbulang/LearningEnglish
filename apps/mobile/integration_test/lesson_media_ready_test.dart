import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/main.dart' as app;

/// Follow-up capture: the main walkthrough screenshots the lesson/speaking
/// screens while DashScope media is still generating. Real media lands a few
/// minutes after confirm, so this re-enters the (already authenticated) session
/// and re-captures the hero screens once audio/images are ready.
///
/// The driver resets the `screenshots/` directory on startup, so collect the
/// walkthrough's screenshots before running this follow-up (it only writes the
/// 08b/08c/11b ready captures).
///
/// Requires the material id created by the walkthrough run and the harness
/// backend (via --dart-define), e.g.:
///   flutter drive --driver=test_driver/integration_test.dart \
///     --target=integration_test/lesson_media_ready_test.dart -d SIM_ID \
///     --dart-define=API_BASE_URL=http://127.0.0.1:8010/v1 \
///     --dart-define=MATERIAL_ID=material_xxx
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('lesson detail + speaking with ready media', (tester) async {
    // Tolerate cosmetic layout overflow / disposed-widget lookups from screen
    // transitions; the screenshot still captures them and they are not flow
    // failures. Every other error still propagates.
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

    const materialId = String.fromEnvironment('MATERIAL_ID');
    expect(materialId, isNotEmpty,
        reason: 'pass --dart-define=MATERIAL_ID=<id> from the walkthrough run; '
            'there is no safe default because each run creates a new material');

    Future<Finder> waitFor(Finder f,
        {Duration timeout = const Duration(seconds: 20)}) async {
      final end = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(end)) {
        await tester.pump(const Duration(milliseconds: 400));
        if (f.evaluate().isNotEmpty) return f;
      }
      throw StateError('"$f" did not appear within $timeout');
    }

    await app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));
    await binding.convertFlutterSurfaceToImage();
    await tester.pumpAndSettle();

    final container =
        ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    // Let the persisted session re-authenticate from the keychain.
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Poll the backend until an asset has BOTH its image and at least one TTS
    // accent ready, so the "ready" capture shows real audio + image instead of a
    // "生成中"/failed placeholder. Real media can finish partial (only TTS or
    // only the image), so requiring a single fully-ready asset is what makes the
    // hero shot trustworthy. Real DashScope generation can take 2-3 minutes.
    final repo = container.read(appRepositoryProvider);
    var mediaReady = false;
    final deadline = DateTime.now().add(const Duration(seconds: 240));
    while (DateTime.now().isBefore(deadline)) {
      try {
        final material = await repo.getMaterial(materialId);
        final ready = material.learningAssets.any((a) =>
            a.generatedImageStatus == 'ready' &&
            (a.ttsUsStatus == 'ready' || a.ttsUkStatus == 'ready'));
        if (ready) {
          mediaReady = true;
          break;
        }
      } catch (_) {
        // transient (auth still settling / network); retry until the deadline
      }
      await tester.pump(const Duration(seconds: 3));
    }
    expect(mediaReady, isTrue,
        reason: 'no asset reached fully-ready media (image + audio) for '
            '$materialId within timeout');

    container.read(appRouterProvider).go('/lessons/$materialId');
    await waitFor(find.text('课程详情'), timeout: const Duration(seconds: 20));
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await binding.takeScreenshot('08b-lesson-media-ready');

    // Scroll to reveal the generated image + 美式/英式 audio controls.
    final scrollable = find.byType(Scrollable);
    if (scrollable.evaluate().isNotEmpty) {
      await tester.drag(scrollable.first, const Offset(0, -420));
      await tester.pumpAndSettle(const Duration(seconds: 1));
      await binding.takeScreenshot('08c-lesson-assets');
    }

    container.read(appRouterProvider).go('/review/speaking/$materialId');
    await waitFor(find.text('口语陪练'), timeout: const Duration(seconds: 15));
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await binding.takeScreenshot('11b-speaking-ready');
  }, timeout: const Timeout(Duration(minutes: 6)));
}
