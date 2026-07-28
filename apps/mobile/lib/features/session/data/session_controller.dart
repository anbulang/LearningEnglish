import 'dart:convert';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

import '../../../core/network/api_error.dart';
import '../../../core/storage/secure_storage.dart';
import '../../auth/data/auth_repository.dart';
import 'session_models.dart';

final sessionControllerProvider =
    StateNotifierProvider<SessionController, SessionState>((ref) {
  return SessionController(
    authRepository: ref.watch(authRepositoryProvider),
    storage: ref.watch(secureStorageProvider),
  )..bootstrap();
});

final accessTokenProvider = Provider<String?>((ref) {
  return ref.watch(sessionControllerProvider).accessToken;
});

class SessionController extends StateNotifier<SessionState> {
  SessionController({
    required AuthRepository authRepository,
    required SecureStorageService storage,
  })  : _authRepository = authRepository,
        _storage = storage,
        super(SessionState.initial);

  final AuthRepository _authRepository;
  final SecureStorageService _storage;

  static const _accessTokenKey = 'session.accessToken';
  static const _refreshTokenKey = 'session.refreshToken';
  static const _childrenKey = 'session.children';
  static const _parentKey = 'session.parent';
  static const _currentChildKey = 'session.currentChildId';
  static const _deviceWechatCodeKey = 'session.deviceWechatCode';

  /// A stable per-install WeChat auth code so each device maps to its own
  /// parent account. Without this every device shares one hardcoded code and
  /// collapses into a single shared account (families would see each other's
  /// children/materials). Generated once and reused across logins.
  ///
  /// NOTE: pilot-grade isolation only — real account identity still requires a
  /// real WeChat OAuth / SMS gateway on the backend.
  Future<String> _deviceWechatCode() async {
    final existing = await _storage.read(_deviceWechatCodeKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final random = Random.secure();
    final suffix = List<int>.generate(16, (_) => random.nextInt(16))
        .map((value) => value.toRadixString(16))
        .join();
    final code = 'mobile-wechat-parent-$suffix';
    await _storage.write(_deviceWechatCodeKey, code);
    return code;
  }

  Future<void> bootstrap() async {
    try {
      // iOS shows the WLAN/cellular data prompt only after the app makes
      // an actual network request. Run this before session restore so the
      // permission is requested on cold start, not only after tapping login.
      await _authRepository.preflightNetworkPermission();
    } catch (_) {
      // Continue bootstrapping. The login screen has the user-facing retry
      // guidance, and refresh/login calls will surface concrete API errors.
    }

    final accessToken = await _storage.read(_accessTokenKey);
    final refreshToken = await _storage.read(_refreshTokenKey);
    if (refreshToken == null) {
      state = state.copyWith(
          stage: SessionStage.signedOut, clearError: true, clearTokens: true);
      return;
    }
    try {
      final result = await _authRepository.refresh(refreshToken);
      await _persistAuthenticated(result);
    } on DioException {
      await clearSession();
    } catch (_) {
      if (accessToken != null) {
        final cachedParent = await _storage.read(_parentKey);
        final cachedChildren = await _storage.read(_childrenKey);
        final currentChildId = await _storage.read(_currentChildKey);
        if (cachedParent != null && cachedChildren != null) {
          state = state.copyWith(
            stage: SessionStage.authenticated,
            parent: ParentAccount.fromJson(
                jsonDecode(cachedParent) as Map<String, dynamic>),
            children: (jsonDecode(cachedChildren) as List<dynamic>)
                .map((item) =>
                    ChildProfile.fromJson(item as Map<String, dynamic>))
                .toList(),
            currentChildId: currentChildId,
            accessToken: accessToken,
            refreshToken: refreshToken,
            isBusy: false,
            clearError: true,
          );
          return;
        }
      }
      await clearSession();
    }
  }

  Future<bool> refreshSession() async {
    final refreshToken =
        state.refreshToken ?? await _storage.read(_refreshTokenKey);
    if (refreshToken == null) {
      await clearSession();
      return false;
    }
    try {
      final result = await _authRepository.refresh(refreshToken);
      await _persistAuthenticated(result);
      return true;
    } on DioException {
      await clearSession();
      return false;
    } catch (_) {
      await clearSession();
      return false;
    }
  }

  Future<void> beginWechatLogin() async {
    state = state.copyWith(isBusy: true, clearError: true);
    try {
      final result =
          await _authRepository.loginWithWechat(await _deviceWechatCode());
      if (result.status == AuthFlowStatus.phoneBindingRequired) {
        state = state.copyWith(
          stage: SessionStage.phoneBindingRequired,
          parent: result.parent,
          bindToken: result.bindToken,
          isBusy: false,
        );
        return;
      }
      await _persistAuthenticated(result);
    } on DioException catch (error) {
      state = state.copyWith(
        stage: SessionStage.signedOut,
        isBusy: false,
        errorMessage: describeApiError(error, fallback: '微信登录失败'),
      );
    }
  }

  Future<String?> requestOtp(String phoneNumber) async {
    final bindToken = state.bindToken;
    if (bindToken == null) {
      state = state.copyWith(errorMessage: '登录状态已失效，请返回重新登录。');
      return null;
    }
    state = state.copyWith(isBusy: true, clearError: true);
    try {
      final otpCode = await _authRepository.requestPhoneOtp(
        bindToken: bindToken,
        phoneNumber: phoneNumber,
      );
      state = state.copyWith(isBusy: false);
      return otpCode;
    } on DioException catch (error) {
      state = state.copyWith(
        isBusy: false,
        errorMessage: describeApiError(error, fallback: '验证码发送失败'),
      );
      return null;
    }
  }

  Future<void> bindPhone({
    required String phoneNumber,
    required String otpCode,
  }) async {
    final bindToken = state.bindToken;
    if (bindToken == null) {
      state = state.copyWith(errorMessage: '登录状态已失效，请返回重新登录。');
      return;
    }
    state = state.copyWith(isBusy: true, clearError: true);
    try {
      final result = await _authRepository.bindPhone(
        bindToken: bindToken,
        phoneNumber: phoneNumber,
        otpCode: otpCode,
      );
      await _persistAuthenticated(result);
    } on DioException catch (error) {
      state = state.copyWith(
        isBusy: false,
        errorMessage: describeApiError(error, fallback: '手机号绑定失败'),
      );
    }
  }

  Future<void> logout() async {
    final refreshToken = state.refreshToken;
    if (refreshToken != null) {
      try {
        await _authRepository.logout(refreshToken);
      } catch (_) {}
    }
    await clearSession();
  }

  Future<void> selectChild(String childId) async {
    await _storage.write(_currentChildKey, childId);
    state = state.copyWith(currentChildId: childId);
  }

  Future<void> addChild(ChildProfile child) async {
    final children = <ChildProfile>[...state.children, child];
    await _storage.write(
      _childrenKey,
      jsonEncode(children.map((item) => item.toJson()).toList()),
    );
    await _storage.write(_currentChildKey, child.id);
    state = state.copyWith(children: children, currentChildId: child.id);
  }

  /// Replaces an existing child (matched by id) with an updated profile, e.g.
  /// after a PATCH that changed the accent. No-op when the id is unknown.
  Future<void> updateChild(ChildProfile child) async {
    final index = state.children.indexWhere((item) => item.id == child.id);
    if (index < 0) {
      return;
    }
    final children = <ChildProfile>[...state.children];
    children[index] = child;
    await _storage.write(
      _childrenKey,
      jsonEncode(children.map((item) => item.toJson()).toList()),
    );
    state = state.copyWith(children: children);
  }

  Future<void> clearSession() async {
    await _storage.deleteMany(const <String>[
      _accessTokenKey,
      _refreshTokenKey,
      _childrenKey,
      _parentKey,
      _currentChildKey,
    ]);
    state = SessionState.initial.copyWith(
      stage: SessionStage.signedOut,
      isBusy: false,
      clearTokens: true,
      clearBindToken: true,
      clearError: true,
    );
  }

  Future<void> _persistAuthenticated(AuthFlowResult result) async {
    final tokens = result.tokens;
    // Preserve the parent's currently selected child across refresh/re-login
    // instead of silently snapping back to children.first.
    final existingChildId =
        state.currentChildId ?? await _storage.read(_currentChildKey);
    final currentChildId = result.children.isEmpty
        ? null
        : (result.children.any((child) => child.id == existingChildId)
            ? existingChildId
            : result.children.first.id);
    if (tokens != null) {
      await _storage.write(_accessTokenKey, tokens.accessToken);
      await _storage.write(_refreshTokenKey, tokens.refreshToken);
    }
    await _storage.write(
        _parentKey,
        jsonEncode(<String, dynamic>{
          'id': result.parent.id,
          'display_name': result.parent.displayName,
          'avatar_url': result.parent.avatarUrl,
          'phone_number': result.parent.phoneNumber,
        }));
    await _storage.write(
      _childrenKey,
      jsonEncode(result.children.map((item) => item.toJson()).toList()),
    );
    if (currentChildId != null) {
      await _storage.write(_currentChildKey, currentChildId);
    }
    state = state.copyWith(
      stage: SessionStage.authenticated,
      parent: result.parent,
      children: result.children,
      currentChildId: currentChildId,
      bindToken: null,
      accessToken: tokens?.accessToken ?? state.accessToken,
      refreshToken: tokens?.refreshToken ?? state.refreshToken,
      isBusy: false,
      clearError: true,
      clearBindToken: true,
    );
  }
}
