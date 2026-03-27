import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

import '../../../core/network/api_client.dart';
import '../../session/data/session_models.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider).raw);
});

class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  Future<AuthFlowResult> loginWithWechat(String authCode) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/wechat/login',
      data: <String, dynamic>{'auth_code': authCode},
    );
    return AuthFlowResult.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<String> requestPhoneOtp({
    required String bindToken,
    required String phoneNumber,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/phone/request-otp',
      data: <String, dynamic>{
        'bind_token': bindToken,
        'phone_number': phoneNumber,
      },
    );
    final payload = response.data ?? const <String, dynamic>{};
    return (payload['debug_code'] ?? '') as String;
  }

  Future<AuthFlowResult> bindPhone({
    required String bindToken,
    required String phoneNumber,
    required String otpCode,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/phone/bind',
      data: <String, dynamic>{
        'bind_token': bindToken,
        'phone_number': phoneNumber,
        'otp_code': otpCode,
      },
    );
    return AuthFlowResult.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<AuthFlowResult> refresh(String refreshToken) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/refresh',
      data: <String, dynamic>{'refresh_token': refreshToken},
    );
    return AuthFlowResult.fromJson(response.data ?? const <String, dynamic>{});
  }

  Future<void> logout(String refreshToken) async {
    await _dio.post<void>(
      '/auth/logout',
      data: <String, dynamic>{'refresh_token': refreshToken},
    );
  }

  Future<AuthFlowResult> getMe(String accessToken) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/me',
      options: Options(headers: <String, dynamic>{'Authorization': 'Bearer $accessToken'}),
    );
    final payload = response.data ?? const <String, dynamic>{};
    return AuthFlowResult(
      status: AuthFlowStatus.authenticated,
      parent: ParentAccount.fromJson(payload['parent_account'] as Map<String, dynamic>? ?? const <String, dynamic>{}),
      children: (payload['children'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => ChildProfile.fromJson(item as Map<String, dynamic>))
          .toList(),
      bindToken: null,
      tokens: AuthTokens(accessToken: accessToken, refreshToken: ''),
    );
  }
}

enum AuthFlowStatus {
  authenticated,
  phoneBindingRequired,
}

class AuthFlowResult {
  const AuthFlowResult({
    required this.status,
    required this.parent,
    required this.children,
    required this.bindToken,
    required this.tokens,
  });

  final String? bindToken;
  final List<ChildProfile> children;
  final ParentAccount parent;
  final AuthFlowStatus status;
  final AuthTokens? tokens;

  factory AuthFlowResult.fromJson(Map<String, dynamic> json) {
    final statusValue = (json['status'] ?? 'phone_binding_required') as String;
    final tokenJson = json['tokens'] as Map<String, dynamic>?;
    return AuthFlowResult(
      status: statusValue == 'authenticated'
          ? AuthFlowStatus.authenticated
          : AuthFlowStatus.phoneBindingRequired,
      parent: ParentAccount.fromJson(json['parent_account'] as Map<String, dynamic>? ?? const <String, dynamic>{}),
      children: (json['children'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => ChildProfile.fromJson(item as Map<String, dynamic>))
          .toList(),
      bindToken: json['bind_token'] as String?,
      tokens: tokenJson == null
          ? null
          : AuthTokens(
              accessToken: tokenJson['access_token'] as String,
              refreshToken: tokenJson['refresh_token'] as String,
            ),
    );
  }
}
