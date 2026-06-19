import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:learning_english_mobile/app/routing/app_router.dart';
import 'package:learning_english_mobile/core/network/api_client.dart';
import 'package:learning_english_mobile/core/network/server_config.dart';
import 'package:learning_english_mobile/main.dart' as app;

/// Follow-up capture: the main walkthrough screenshots the lesson/speaking
/// screens while DashScope media is still generating ("生成中"). Real media
/// finishes ~2-3 min later, so this re-enters the (already authenticated)
/// session and re-captures the hero screens once audio + images are ready.
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('lesson detail + speaking with ready media', (tester) async {
    const materialId = String.fromEnvironment('MATERIAL_ID',
        defaultValue: 'material_79cf5b99a7f9');

    await app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));
    await binding.convertFlutterSurfaceToImage();
    await tester.pumpAndSettle();

    final container =
        ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    await container.read(serverConfigProvider).clearOverride();
    container.read(apiClientProvider).baseUrl = 'http://127.0.0.1:8010/v1';
    // Let the persisted session re-authenticate from the keychain.
    await tester.pumpAndSettle(const Duration(seconds: 2));

    final router = container.read(appRouterProvider);
    router.go('/lessons/$materialId');
    // Lesson detail re-polls media on mount; give it a few seconds to settle.
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(seconds: 1));
    }
    await binding.takeScreenshot('08b-lesson-media-ready');

    // Scroll to reveal the generated image + 听发音 buttons.
    final scrollable = find.byType(Scrollable);
    if (scrollable.evaluate().isNotEmpty) {
      await tester.drag(scrollable.first, const Offset(0, -420));
      await tester.pumpAndSettle(const Duration(seconds: 1));
      await binding.takeScreenshot('08c-lesson-assets');
    }

    router.go('/review/speaking/$materialId');
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(seconds: 1));
    }
    await binding.takeScreenshot('11b-speaking-ready');
  }, timeout: const Timeout(Duration(minutes: 3)));
}
