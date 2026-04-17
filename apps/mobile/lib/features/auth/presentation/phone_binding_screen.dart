import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../session/data/session_controller.dart';

class PhoneBindingScreen extends ConsumerStatefulWidget {
  const PhoneBindingScreen({super.key});

  @override
  ConsumerState<PhoneBindingScreen> createState() => _PhoneBindingScreenState();
}

class _PhoneBindingScreenState extends ConsumerState<PhoneBindingScreen> {
  final _phoneController = TextEditingController(text: '13800138000');
  final _otpController = TextEditingController(text: '123456');
  String? _debugOtp;

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(color: AppColors.warmLinen),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: ListView(
                shrinkWrap: true,
                children: <Widget>[
                  const IllustratedHeroCard(
                    eyebrow: '账号安全',
                    title: '绑定手机号，后面提醒和账号恢复都会更省心',
                    description: '首次登录需要补一次手机号绑定。开发环境会直接返回验证码，方便完整体验整条复习流程。',
                    accent: AppColors.skyBlue,
                    illustration: Icons.phone_iphone_rounded,
                    badge: StickerBadge(label: '开发模式', icon: Icons.sms_rounded, color: AppColors.butterYellow),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppCard(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('绑定手机号', style: AppTextStyles.pageTitle),
                        const SizedBox(height: AppSpacing.sm),
                        const Text('首次登录需要绑定手机号，用来恢复家长账号和后续通知。'),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: _phoneController,
                          decoration: const InputDecoration(labelText: '手机号'),
                          keyboardType: TextInputType.phone,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: TextField(
                                controller: _otpController,
                                decoration: const InputDecoration(labelText: '验证码'),
                                keyboardType: TextInputType.number,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            OutlinedButton(
                              onPressed: session.isBusy
                                  ? null
                                  : () async {
                                      final otp = await ref
                                          .read(sessionControllerProvider.notifier)
                                          .requestOtp(_phoneController.text.trim());
                                      if (!mounted) {
                                        return;
                                      }
                                      setState(() {
                                        _debugOtp = otp;
                                        if (otp != null && otp.isNotEmpty) {
                                          _otpController.text = otp;
                                        }
                                      });
                                    },
                              child: const Text('获取验证码'),
                            ),
                          ],
                        ),
                        if (_debugOtp != null) ...<Widget>[
                          const SizedBox(height: AppSpacing.sm),
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            decoration: BoxDecoration(
                              color: AppColors.butterYellow.withValues(alpha: 0.32),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Text('开发环境验证码：$_debugOtp', style: AppTextStyles.helper),
                          ),
                        ],
                        if (session.errorMessage != null) ...<Widget>[
                          const SizedBox(height: AppSpacing.md),
                          StatePanel(
                            title: '绑定失败',
                            description: session.errorMessage!,
                            icon: Icons.error_outline_rounded,
                          ),
                        ],
                        const SizedBox(height: AppSpacing.lg),
                        FilledButton(
                          onPressed: session.isBusy
                              ? null
                              : () => ref.read(sessionControllerProvider.notifier).bindPhone(
                                    phoneNumber: _phoneController.text.trim(),
                                    otpCode: _otpController.text.trim(),
                                  ),
                          child: Text(session.isBusy ? '提交中...' : '完成绑定'),
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
