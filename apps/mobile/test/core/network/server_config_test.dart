import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_mobile/core/network/server_config.dart';

void main() {
  group('ServerConfig.isValidBaseUrl', () {
    test('accepts absolute http(s) URLs that include the /v1 prefix', () {
      expect(ServerConfig.isValidBaseUrl('https://api.example.com/v1'), isTrue);
      expect(ServerConfig.isValidBaseUrl('http://192.168.1.10:8000/v1'), isTrue);
      expect(ServerConfig.isValidBaseUrl('  https://api.example.com/v1  '), isTrue);
    });

    test('rejects empty, relative, or non-http schemes', () {
      expect(ServerConfig.isValidBaseUrl(''), isFalse);
      expect(ServerConfig.isValidBaseUrl('   '), isFalse);
      expect(ServerConfig.isValidBaseUrl('api.example.com/v1'), isFalse);
      expect(ServerConfig.isValidBaseUrl('ftp://api.example.com'), isFalse);
    });

    test('rejects a base URL missing the /v1 API prefix', () {
      // A bare host would 404 every request — reject it instead of failing later.
      expect(ServerConfig.isValidBaseUrl('https://api.example.com'), isFalse);
      expect(ServerConfig.isValidBaseUrl('https://api.example.com/'), isFalse);
      expect(ServerConfig.isValidBaseUrl('https://api.example.com/v2'), isFalse);
    });
  });
}
