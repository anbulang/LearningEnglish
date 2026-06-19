import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

Future<void> main() async {
  // Start from a clean output directory so stale screenshots from a previous
  // run (e.g. ERROR-*, the optional 07b-*, or follow-up shots) cannot linger
  // and corrupt the captured set.
  final outDir = Directory('screenshots');
  if (outDir.existsSync()) {
    outDir.deleteSync(recursive: true);
  }
  outDir.createSync(recursive: true);
  await integrationDriver(
    onScreenshot:
        (String name, List<int> bytes, [Map<String, Object?>? args]) async {
      final file = File('screenshots/$name.png');
      await file.create(recursive: true);
      await file.writeAsBytes(bytes);
      return true;
    },
  );
}
