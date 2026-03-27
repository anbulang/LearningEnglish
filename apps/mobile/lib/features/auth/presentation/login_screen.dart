import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/state_panel.dart';
import '../../session/data/session_controller.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: AppCard(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('LearningEnglish', style: AppTextStyles.pageTitle),
                  const SizedBox(height: AppSpacing.sm),
                  const Text('先用微信登录家长账号，再绑定手机号进入讲义复习流。'),
                  const SizedBox(height: AppSpacing.lg),
                  if (session.errorMessage != null) ...<Widget>[
                    StatePanel(
                      title: '登录失败',
                      description: session.errorMessage!,
                      icon: Icons.error_outline_rounded,
                    ),
                    const SizedBox(height: AppSpacing.md),
                  ],
                  FilledButton.icon(
                    onPressed: session.isBusy
                        ? null
                        : () => ref.read(sessionControllerProvider.notifier).beginWechatLogin(),
                    icon: const Icon(Icons.chat_bubble_outline_rounded),
                    label: Text(session.isBusy ? '登录中...' : '微信登录'),
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
