import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

class ApiClient {
  ApiClient({Dio? dio, String? baseUrl})
      : _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: (baseUrl != null && baseUrl.trim().isNotEmpty)
                    ? baseUrl.trim()
                    : defaultBaseUrl,
                connectTimeout: const Duration(seconds: 30),
                receiveTimeout: const Duration(seconds: 30),
              ),
            );

  static const defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000/v1',
  );

  final Dio _dio;

  Dio get raw => _dio;

  /// The base URL all requests are currently issued against.
  String get baseUrl => _dio.options.baseUrl;

  /// Repoints the live client at [value] so a server-address change takes
  /// effect without restarting the app.
  set baseUrl(String value) {
    final trimmed = value.trim();
    if (trimmed.isNotEmpty) {
      _dio.options.baseUrl = trimmed;
    }
  }
}
