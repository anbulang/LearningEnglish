import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'app/app.dart';
import 'core/network/api_client.dart';
import 'core/network/server_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final baseUrl =
      await ServerConfig(const FlutterSecureStorage()).resolveBaseUrl();
  runApp(
    ProviderScope(
      overrides: <Override>[
        apiClientProvider.overrideWith((ref) => ApiClient(baseUrl: baseUrl)),
      ],
      child: const LearningEnglishApp(),
    ),
  );
}
