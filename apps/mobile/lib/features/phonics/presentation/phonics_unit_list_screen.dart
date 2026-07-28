import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/no_child_state_panel.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';
import '../data/phonics_providers.dart';

class PhonicsUnitListScreen extends ConsumerWidget {
  const PhonicsUnitListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    final unitsAsync = ref.watch(phonicsUnitsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('自然拼读')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: child == null
            ? const NoChildStatePanel(description: '自然拼读需要先为孩子建立档案。')
            : unitsAsync.when(
                data: (response) {
                  if (response == null) {
                    return const NoChildStatePanel(
                        description: '自然拼读需要先为孩子建立档案。');
                  }
                  return _PhonicsUnitList(response: response);
                },
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (error, _) => StatePanel(
                  title: '拼读课加载失败',
                  description:
                      describeApiError(error, fallback: '拼读课加载失败，请稍后重试。'),
                  assetPath: AppIllustrations.stateError,
                  action: FilledButton(
                    onPressed: () => ref.invalidate(phonicsUnitsProvider),
                    child: const Text('重新加载'),
                  ),
                ),
              ),
      ),
    );
  }
}

class _PhonicsUnitList extends StatelessWidget {
  const _PhonicsUnitList({required this.response});

  final PhonicsUnitListResponse response;

  @override
  Widget build(BuildContext context) {
    final units = response.units;
    final masteredCount =
        units.where((unit) => unit.status == PhonicsUnitStatus.mastered).length;

    return ListView(
      children: <Widget>[
        IllustratedHeroCard(
          eyebrow: '自然拼读',
          title: response.course.title.isEmpty ? '自然拼读' : response.course.title,
          description: response.course.description.isEmpty
              ? '听音识音 → 圈首音 → 拼读 → 高频词，一步步学会自己拼读单词。'
              : response.course.description,
          accent: AppColors.skyBlue,
          illustration: Icons.abc_rounded,
          assetPath: AppIllustrations.topicPhonics,
          badge: StickerBadge(
            label: '已掌握 $masteredCount/${units.length}',
            icon: Icons.workspace_premium_rounded,
            color: AppColors.mintLeaf,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        if (units.isEmpty)
          const StatePanel(
            title: '暂时还没有拼读课',
            description: '拼读课程正在准备中，稍后再来看看吧。',
            assetPath: AppIllustrations.stateEmpty,
          )
        else
          ...units.map(
            (unit) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: _PhonicsUnitCard(unit: unit),
            ),
          ),
      ],
    );
  }
}

class _PhonicsUnitCard extends StatelessWidget {
  const _PhonicsUnitCard({required this.unit});

  final PhonicsUnitSummary unit;

  @override
  Widget build(BuildContext context) {
    final locked = unit.status == PhonicsUnitStatus.locked;
    final badge = _statusBadge(unit.status);
    final showAccuracy = unit.status == PhonicsUnitStatus.inProgress ||
        unit.status == PhonicsUnitStatus.mastered;

    final card = Opacity(
      opacity: locked ? 0.55 : 1,
      child: AppCard(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 48,
              height: 48,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: badge.color.withValues(alpha: 0.22),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(unit.unitCode, style: AppTextStyles.helper),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(unit.title, style: AppTextStyles.cardTitle),
                  const SizedBox(height: AppSpacing.xxs),
                  Text(unit.subtitle, style: AppTextStyles.body),
                  const SizedBox(height: AppSpacing.sm),
                  Row(
                    children: <Widget>[
                      _StatusPill(badge: badge),
                      if (showAccuracy) ...<Widget>[
                        const SizedBox(width: AppSpacing.sm),
                        Text('拼读正确率 ${(unit.decodingAccuracy * 100).round()}%',
                            style: AppTextStyles.helper),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Icon(
              locked ? Icons.lock_rounded : Icons.chevron_right_rounded,
              color: AppColors.dustBrown,
            ),
          ],
        ),
      ),
    );

    if (locked) {
      // Locked units are intentionally non-tappable — no InkWell, no navigation.
      return Semantics(
        label: '${unit.title}（未解锁）',
        child: card,
      );
    }

    return InkWell(
      borderRadius: BorderRadius.circular(AppRadii.card),
      onTap: () => context.push('/phonics/unit/${unit.id}'),
      child: card,
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.badge});

  final _StatusBadge badge;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm, vertical: AppSpacing.xxs),
      decoration: BoxDecoration(
        color: badge.color.withValues(alpha: 0.28),
        borderRadius: BorderRadius.circular(AppRadii.pill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(badge.icon, size: 14, color: AppColors.cocoaCoral),
          const SizedBox(width: AppSpacing.xxs),
          Text(badge.label, style: AppTextStyles.helper),
        ],
      ),
    );
  }
}

_StatusBadge _statusBadge(PhonicsUnitStatus status) {
  switch (status) {
    case PhonicsUnitStatus.locked:
      return const _StatusBadge(
          label: '未解锁',
          color: AppColors.outlineVariant,
          icon: Icons.lock_rounded);
    case PhonicsUnitStatus.unlocked:
      return const _StatusBadge(
          label: '可开始',
          color: AppColors.skyBlue,
          icon: Icons.play_circle_outline_rounded);
    case PhonicsUnitStatus.inProgress:
      return const _StatusBadge(
          label: '学习中',
          color: AppColors.butterYellow,
          icon: Icons.timelapse_rounded);
    case PhonicsUnitStatus.mastered:
      return const _StatusBadge(
          label: '已掌握',
          color: AppColors.mintLeaf,
          icon: Icons.workspace_premium_rounded);
  }
}

class _StatusBadge {
  const _StatusBadge({
    required this.label,
    required this.color,
    required this.icon,
  });

  final Color color;
  final IconData icon;
  final String label;
}
