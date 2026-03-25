import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/widgets/app_card.dart';
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

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);
    final attempt = ref.watch(lastSpeakingAttemptProvider);
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
                onPressed: () {
                  if (_submitted) {
                    return;
                  }
                  ref.read(lastSpeakingAttemptProvider.notifier).state = SpeakingAttempt(
                    id: 'attempt_demo_1',
                    childId: 'child_demo_1',
                    materialId: widget.materialId,
                    promptText: 'What is this?',
                    audioUrl: '',
                    transcript: 'It is a cat.',
                    pronunciationScore: 0.86,
                    feedback: 'Great job! 把 cat 的结尾再收紧一点会更自然。',
                    status: SpeakingAttemptStatus.scored,
                  );
                  ref.read(weeklyReportProvider.notifier).registerSpeakingAttempt();
                  ref.read(appAnalyticsProvider).track('speaking_attempt_submitted', {
                    'materialId': widget.materialId,
                  });
                  setState(() {
                    _submitted = true;
                  });
                },
                icon: const Icon(Icons.mic_rounded),
                label: const Text('提交回答'),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  ref.read(lastSpeakingAttemptProvider.notifier).state = null;
                  setState(() {
                    _submitted = false;
                  });
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重试'),
              ),
            ],
          ),
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
        child: formFactor.isTablet
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
