import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';

class SpeakingPartnerScreen extends ConsumerStatefulWidget {
  const SpeakingPartnerScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  ConsumerState<SpeakingPartnerScreen> createState() => _SpeakingPartnerScreenState();
}

class _SpeakingPartnerScreenState extends ConsumerState<SpeakingPartnerScreen> {
  bool _submitted = false;
  String? _errorMessage;

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);
    final attempt = ref.watch(lastSpeakingAttemptProvider);
    final child = ref.watch(activeChildProvider);
    final stage = AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('AI 口语陪练', style: AppTextStyles.pageTitle),
          const SizedBox(height: AppSpacing.sm),
          const Text('老师提问：What is this?'),
          const SizedBox(height: AppSpacing.md),
          Container(
            height: 180,
            decoration: BoxDecoration(
              color: AppColors.softSheet,
              borderRadius: BorderRadius.circular(AppRadii.panel),
            ),
            child: const Center(
              child: Icon(Icons.record_voice_over_rounded, size: 72),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton.icon(
                onPressed: () async {
                  if (_submitted || child == null) {
                    return;
                  }
                  try {
                    final created = await ref.read(appRepositoryProvider).createSpeakingAttempt(
                          childId: child.id,
                          materialId: widget.materialId,
                          promptText: 'What is this?',
                          transcript: 'It is a cat.',
                        );
                    ref.read(lastSpeakingAttemptProvider.notifier).state = created;
                    ref.invalidate(weeklyReportProvider);
                    ref.read(appAnalyticsProvider).track('speaking_attempt_submitted', {
                      'materialId': widget.materialId,
                    });
                    setState(() {
                      _submitted = true;
                      _errorMessage = null;
                    });
                  } catch (error) {
                    setState(() {
                      _errorMessage = describeApiError(error, fallback: '口语提交失败，请稍后重试。');
                    });
                  }
                },
                icon: const Icon(Icons.mic_rounded),
                label: const Text('提交回答'),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  ref.read(lastSpeakingAttemptProvider.notifier).state = null;
                  setState(() {
                    _submitted = false;
                    _errorMessage = null;
                  });
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重试'),
              ),
            ],
          ),
          if (_errorMessage != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            StatePanel(
              title: '提交失败',
              description: _errorMessage!,
              icon: Icons.error_outline_rounded,
            ),
          ],
        ],
      ),
    );

    final result = AppCard(
      child: attempt == null
          ? const Text('提交一次回答后，这里会显示转写和反馈。')
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('识别结果', style: AppTextStyles.sectionTitle),
                const SizedBox(height: AppSpacing.sm),
                Text('你说的是：${attempt.transcript}'),
                const SizedBox(height: AppSpacing.xs),
                Text('发音评分：${(attempt.pronunciationScore ?? 0) * 100 ~/ 1}%'),
                const SizedBox(height: AppSpacing.xs),
                Text(attempt.feedback),
              ],
            ),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('口语陪练')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: child == null
            ? const StatePanel(
                title: '缺少孩子档案',
                description: '请先完成家长账号初始化。',
              )
            : formFactor.isTablet
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(child: stage),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(child: result),
                ],
              )
            : ListView(
                children: <Widget>[
                  stage,
                  const SizedBox(height: AppSpacing.md),
                  result,
                ],
              ),
      ),
    );
  }
}
