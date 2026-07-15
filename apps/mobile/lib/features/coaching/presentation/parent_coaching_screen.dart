import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';

class ParentCoachingScreen extends ConsumerWidget {
  const ParentCoachingScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scriptAsync = ref.watch(parentCoachingScriptProvider(materialId));
    final formFactor = formFactorOf(context);

    final scriptPanel = scriptAsync.when(
      data: (script) => AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            IllustratedHeroCard(
              eyebrow: '亲子陪练',
              title: script.title,
              description: script.intro,
              accent: AppColors.coralJam,
              illustration: Icons.favorite_rounded,
              assetPath: AppIllustrations.heroParentCoaching,
              badge: const StickerBadge(
                  label: '家长跟着说', icon: Icons.record_voice_over_rounded),
            ),
            const SizedBox(height: AppSpacing.md),
            ...script.steps.map(
              (step) => Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.md),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Text(step.title, style: AppTextStyles.cardTitle),
                          const SizedBox(width: AppSpacing.sm),
                          const StickerBadge(
                              label: '陪练步骤', color: AppColors.butterYellow),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text('现在怎么说：${step.parentPrompt}'),
                      const SizedBox(height: AppSpacing.xs),
                      Text('孩子卡住时：${step.stuckHint}'),
                      const SizedBox(height: AppSpacing.xs),
                      Text('继续扩展：${step.expansionPrompt}'),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: <Widget>[
                FilledButton(
                  onPressed: () => context.go('/lessons/$materialId'),
                  child: const Text('回到本课'),
                ),
                OutlinedButton(
                  onPressed: () => context.push('/review/speaking/$materialId'),
                  child: const Text('去口语陪练'),
                ),
                TextButton(
                  onPressed: () => context.go('/reports'),
                  child: const Text('查看本周报告'),
                ),
              ],
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => StatePanel(
        title: '亲子陪练脚本加载失败',
        description: describeApiError(error, fallback: '亲子陪练脚本暂时不可用，请稍后重试。'),
        assetPath: AppIllustrations.stateError,
        action: FilledButton(
          onPressed: () =>
              ref.invalidate(parentCoachingScriptProvider(materialId)),
          child: const Text('刷新脚本'),
        ),
      ),
    );

    if (!formFactor.isTablet) {
      return Scaffold(
        appBar: AppBar(title: const Text('亲子陪练')),
        body: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: <Widget>[scriptPanel],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('亲子陪练')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const <Widget>[
                    Text('孩子上下文', style: AppTextStyles.sectionTitle),
                    SizedBox(height: AppSpacing.sm),
                    Text('目标：用 What is this? 和 It is a ... 做 2 轮问答。'),
                    SizedBox(height: AppSpacing.sm),
                    Text('建议：先看图、再听音、再完整说句子。'),
                  ],
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(flex: 2, child: SingleChildScrollView(child: scriptPanel)),
          ],
        ),
      ),
    );
  }
}
