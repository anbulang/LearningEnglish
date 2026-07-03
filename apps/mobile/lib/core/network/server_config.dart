import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_client.dart';

final serverConfigProvider = Provider<ServerConfig>((ref) {
  return ServerConfig(const FlutterSecureStorage());
});

/// Persists an optional override for the backend base URL so an internal tester
/// can repoint the app at a different server without a recompile. When no
/// override is stored the app falls back to [ApiClient.defaultBaseUrl] (the
/// compile-time `API_BASE_URL`).
class ServerConfig {
  ServerConfig(this._storage);

  static const storageKey = 'api_base_url_override';

  final FlutterSecureStorage _storage;

  Future<String?> readOverride() async {
    final value = await _storage.read(key: storageKey);
    final trimmed = value?.trim() ?? '';
    return trimmed.isEmpty ? null : trimmed;
  }

  Future<String> resolveBaseUrl() async {
    return (await readOverride()) ?? ApiClient.defaultBaseUrl;
  }

  Future<void> saveOverride(String value) async {
    final trimmed = value.trim();
    if (trimmed.isEmpty) {
      await _storage.delete(key: storageKey);
      return;
    }
    await _storage.write(key: storageKey, value: trimmed);
  }

  Future<void> clearOverride() => _storage.delete(key: storageKey);

  /// Whether [value] is a usable absolute http(s) base URL that includes the
  /// `/v1` API prefix. The backend serves the parent API under `/v1`, so a bare
  /// host would 404 every request — reject it here instead of failing silently.
  static bool isValidBaseUrl(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        (uri.scheme != 'http' && uri.scheme != 'https') ||
        uri.host.isEmpty) {
      return false;
    }
    final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    return segments.isNotEmpty && segments.last == 'v1';
  }
}
