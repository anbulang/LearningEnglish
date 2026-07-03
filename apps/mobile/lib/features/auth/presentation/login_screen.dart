import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../data/auth_repository.dart';
import '../../session/data/session_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _isCheckingNetworkPermission = true;
  String? _networkPermissionMessage;

  @override
  void initState() {
    super.initState();
    Future<void>.microtask(_preflightNetworkPermission);
  }

  Future<void> _preflightNetworkPermission() async {
    try {
      await ref.read(authRepositoryProvider).preflightNetworkPermission();
      if (!mounted) {
        return;
      }
      setState(() {
        _isCheckingNetworkPermission = false;
        _networkPermissionMessage = null;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isCheckingNetworkPermission = false;
        _networkPermissionMessage = describeApiError(
          error,
          fallback: '网络权限预检失败，请确认已允许 App 使用无线局域网与蜂窝数据。',
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: <Color>[AppColors.warmLinen, AppColors.softSheet],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  const IllustratedHeroCard(
                    eyebrow: '家长入口',
                    title: '先登录，再把每节外教课变成孩子能复习的小课包',
                    description: '使用微信登录家长账号，接着绑定手机号，就能开始上传课堂讲义和生成互动复习内容。',
                    accent: AppColors.coralJam,
                    illustration: Icons.family_restroom_rounded,
                    assetPath: AppIllustrations.heroLogin,
                    badge: StickerBadge(
                        label: '亲子陪学', icon: Icons.favorite_rounded),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppCard(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('LearningEnglish', style: AppTextStyles.pageTitle),
                        const SizedBox(height: AppSpacing.sm),
                        const Text('先用微信登录家长账号，再绑定手机号进入讲义复习流。'),
                        const SizedBox(height: AppSpacing.lg),
                        if (_isCheckingNetworkPermission ||
                            _networkPermissionMessage != null) ...<Widget>[
                          StatePanel(
                            title: _isCheckingNetworkPermission
                                ? '正在检查网络权限'
                                : '网络权限需要确认',
                            description: _isCheckingNetworkPermission
                                ? '首次打开时，系统可能会询问是否允许使用无线局域网与蜂窝数据，请选择允许。'
                                : '请在系统弹窗中选择允许，或到“设置 > Learning English Mobile > 无线数据”开启 WLAN 与蜂窝数据。\n\n$_networkPermissionMessage',
                            icon: _isCheckingNetworkPermission
                                ? Icons.wifi_find_rounded
                                : Icons.wifi_off_rounded,
                            assetPath: AppIllustrations.stateEmpty,
                            action: _isCheckingNetworkPermission
                                ? null
                                : FilledButton.icon(
                                    onPressed: () {
                                      setState(() {
                                        _isCheckingNetworkPermission = true;
                                        _networkPermissionMessage = null;
                                      });
                                      _preflightNetworkPermission();
                                    },
                                    icon: const Icon(Icons.refresh_rounded),
                                    label: const Text('重新检查网络'),
                                  ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                        ],
                        if (session.errorMessage != null) ...<Widget>[
                          StatePanel(
                            title: '登录失败',
                            description: session.errorMessage!,
                            icon: Icons.error_outline_rounded,
                            assetPath: AppIllustrations.stateError,
                          ),
                          const SizedBox(height: AppSpacing.md),
                        ],
                        FilledButton.icon(
                          onPressed: session.isBusy
                              ? null
                              : () => ref
                                  .read(sessionControllerProvider.notifier)
                                  .beginWechatLogin(),
                          icon: const Icon(Icons.chat_bubble_outline_rounded),
                          label: Text(session.isBusy ? '登录中...' : '微信登录'),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: Text(
                                '当前 API：${ref.watch(apiClientProvider).baseUrl}',
                                style: AppTextStyles.helper.copyWith(
                                  color: AppColors.dustBrown,
                                ),
                              ),
                            ),
                            TextButton(
                              onPressed: () => context.push('/settings/server'),
                              child: const Text('修改'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
