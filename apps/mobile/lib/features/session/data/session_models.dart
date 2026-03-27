import 'package:learning_english_contracts/contracts.dart';

enum SessionStage {
  bootstrapping,
  signedOut,
  phoneBindingRequired,
  authenticated,
}

class ParentAccount {
  const ParentAccount({
    required this.id,
    required this.displayName,
    required this.avatarUrl,
    required this.phoneNumber,
  });

  final String id;
  final String displayName;
  final String avatarUrl;
  final String phoneNumber;

  factory ParentAccount.fromJson(Map<String, dynamic> json) {
    return ParentAccount(
      id: json['id'] as String,
      displayName: json['display_name'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
    );
  }
}

class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
  });

  final String accessToken;
  final String refreshToken;
}

class SessionState {
  const SessionState({
    required this.stage,
    required this.isBusy,
    required this.parent,
    required this.children,
    required this.currentChildId,
    required this.bindToken,
    required this.accessToken,
    required this.refreshToken,
    required this.errorMessage,
  });

  final String? accessToken;
  final String? bindToken;
  final List<ChildProfile> children;
  final String? currentChildId;
  final String? errorMessage;
  final bool isBusy;
  final ParentAccount? parent;
  final String? refreshToken;
  final SessionStage stage;

  static const SessionState initial = SessionState(
    stage: SessionStage.bootstrapping,
    isBusy: false,
    parent: null,
    children: <ChildProfile>[],
    currentChildId: null,
    bindToken: null,
    accessToken: null,
    refreshToken: null,
    errorMessage: null,
  );

  ChildProfile? get activeChild {
    if (children.isEmpty) {
      return null;
    }
    return children.firstWhere(
      (child) => child.id == currentChildId,
      orElse: () => children.first,
    );
  }

  bool get isAuthenticated => stage == SessionStage.authenticated && accessToken != null;

  SessionState copyWith({
    String? accessToken,
    String? bindToken,
    List<ChildProfile>? children,
    String? currentChildId,
    String? errorMessage,
    bool? isBusy,
    ParentAccount? parent,
    String? refreshToken,
    SessionStage? stage,
    bool clearError = false,
    bool clearBindToken = false,
    bool clearTokens = false,
  }) {
    return SessionState(
      stage: stage ?? this.stage,
      isBusy: isBusy ?? this.isBusy,
      parent: parent ?? this.parent,
      children: children ?? this.children,
      currentChildId: currentChildId ?? this.currentChildId,
      bindToken: clearBindToken ? null : (bindToken ?? this.bindToken),
      accessToken: clearTokens ? null : (accessToken ?? this.accessToken),
      refreshToken: clearTokens ? null : (refreshToken ?? this.refreshToken),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}
