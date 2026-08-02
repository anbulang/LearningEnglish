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
import '../../../core/widgets/remote_asset_image.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    if (child == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('报告')),
        body: const Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: NoChildStatePanel(
            description: '添加孩子档案后，系统会开始生成每周复习报告。',
          ),
        ),
      );
    }

    final report = ref.watch(weeklyReportProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('报告')),
      body: report.when(
        data: (value) {
          if (value.assetMastery.isEmpty && value.materialSummaries.isEmpty) {
            // Materials may be archived while weekly counters still exist — only
            // show the fully-empty panel when there's no trend history either,
            // so the 多周趋势 card isn't gated behind active-material summaries.
            final hasTrendHistory = ref.watch(weeklyTrendsProvider).maybeWhen(
                  data: (trends) => trends.points.any(
                      (p) => p.completedSessions > 0 || p.speakingAttempts > 0),
                  orElse: () => false,
                );
            if (!hasTrendHistory) {
              return const Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: StatePanel(
                  title: '还没有报告数据',
                  description: '上传并确认讲义后，报告会按词卡、句子、复习和口语练习自动汇总。',
                  assetPath: AppIllustrations.stateEmpty,
                ),
              );
            }
          }
          return ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: <Widget>[
              IllustratedHeroCard(
                eyebrow: '成长报告',
                title: '${child.name} 的本周学习概览',
                description: value.reportSummary.isEmpty
                    ? '完成 ${value.completedSessions} 次复习，口语练习 ${value.speakingAttempts} 次。'
                    : value.reportSummary,
                accent: AppColors.mintLeaf,
                illustration: Icons.query_stats_rounded,
                assetPath: AppIllustrations.heroWeeklyGrowth,
                badge: StickerBadge(
                  label: '${value.assetMastery.length} 个学习资产',
                  icon: Icons.auto_graph_rounded,
                  color: AppColors.butterYellow,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              _MetricGrid(report: value),
              const SizedBox(height: AppSpacing.md),
              const _TrendsSection(),
              const SizedBox(height: AppSpacing.md),
              _MaterialSummarySection(items: value.materialSummaries),
              const SizedBox(height: AppSpacing.md),
              _AssetMasterySection(items: value.assetMastery),
              if (value.recommendedActions.isNotEmpty) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                _RecommendedActions(items: value.recommendedActions),
              ],
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: isNotFoundApiError(error)
              ? StatePanel(
                  title: '还没有报告数据',
                  description: '上传并确认讲义、完成复习或口语练习后，报告会自动生成。',
                  assetPath: AppIllustrations.stateEmpty,
                  action: FilledButton(
                    onPressed: () => context.go('/materials'),
                    child: const Text('去上传讲义'),
                  ),
                )
              : StatePanel(
                  title: '报告加载失败',
                  description:
                      describeApiError(error, fallback: '报告暂时不可用，请稍后重试。'),
                  assetPath: AppIllustrations.stateError,
                  action: FilledButton.icon(
                    onPressed: () {
                      ref.invalidate(weeklyReportProvider);
                      ref.invalidate(weeklyTrendsProvider);
                    },
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('刷新报告'),
                  ),
                ),
        ),
      ),
    );
  }
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.report});

  final WeeklyReport report;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Wrap(
        spacing: AppSpacing.sm,
        runSpacing: AppSpacing.sm,
        children: <Widget>[
          _MetricTile(
            label: '复习',
            value: '${report.completedSessions}',
            icon: Icons.bookmark_added_rounded,
            accent: AppColors.skyBlue,
          ),
          _MetricTile(
            label: '词句',
            value: '${report.reviewedWords}',
            icon: Icons.style_rounded,
            accent: AppColors.butterYellow,
          ),
          _MetricTile(
            label: '口语',
            value: '${report.speakingAttempts}',
            icon: Icons.mic_rounded,
            accent: AppColors.mintLeaf,
          ),
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final Color accent;
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 96,
      child: Row(
        children: <Widget>[
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: AppColors.cocoaCoral, size: 20),
          ),
          const SizedBox(width: AppSpacing.xs),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(value, style: AppTextStyles.cardTitle),
              Text(label, style: AppTextStyles.helper),
            ],
          ),
        ],
      ),
    );
  }
}

class _TrendsSection extends ConsumerWidget {
  const _TrendsSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trends = ref.watch(weeklyTrendsProvider);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.show_chart_rounded,
                  color: AppColors.cocoaCoral, size: 20),
              const SizedBox(width: AppSpacing.xs),
              Text('多周趋势', style: AppTextStyles.sectionTitle),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text('每周完成复习次数（从旧到新）', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.md),
          trends.when(
            data: (value) => _TrendsChart(points: value.points),
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (error, _) => Text(
              isNotFoundApiError(error)
                  ? '还没有足够的每周数据，坚持练习后这里会显示趋势～'
                  : '趋势暂时不可用，请稍后重试。',
              style: AppTextStyles.helper,
            ),
          ),
        ],
      ),
    );
  }
}

class _TrendsChart extends StatelessWidget {
  const _TrendsChart({required this.points});

  final List<WeeklyTrendPoint> points;

  @override
  Widget build(BuildContext context) {
    if (points.length < 2) {
      return Text(
        '还没有足够的每周数据，坚持练习后这里会显示趋势～',
        style: AppTextStyles.helper,
      );
    }
    final maxValue = points
        .map((p) => p.completedSessions)
        .fold<int>(1, (prev, v) => v > prev ? v : prev);
    const chartHeight = 96.0;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: <Widget>[
        for (final point in points)
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text('${point.completedSessions}',
                    style: AppTextStyles.helper),
                const SizedBox(height: 4),
                Container(
                  width: 18,
                  height: (point.completedSessions / maxValue * chartHeight)
                      .clamp(4.0, chartHeight),
                  decoration: BoxDecoration(
                    color: point.completedSessions == 0
                        ? AppColors.softSheet
                        : AppColors.mintLeaf,
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text('${point.weekStart.month}/${point.weekStart.day}',
                    style: AppTextStyles.helper),
              ],
            ),
          ),
      ],
    );
  }
}

class _MaterialSummarySection extends StatelessWidget {
  const _MaterialSummarySection({required this.items});

  final List<MaterialReportSummary> items;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('讲义汇总', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Row(
                children: <Widget>[
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: AppColors.skyBlue.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.menu_book_rounded,
                        color: AppColors.cocoaCoral),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(item.title, style: AppTextStyles.cardTitle),
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          '${item.assetCount} 个词句 · ${item.completedReviewTasks} 个已复习 · ${item.speakingAttempts} 次口语',
                          style: AppTextStyles.helper,
                        ),
                      ],
                    ),
                  ),
                  if (item.averageSpeakingScore != null)
                    Text('${item.averageSpeakingScore!.round()} 分',
                        style: AppTextStyles.cardTitle),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AssetMasterySection extends StatelessWidget {
  const _AssetMasterySection({required this.items});

  final List<LearningAssetMastery> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
          child: Text('词句掌握度', style: AppTextStyles.sectionTitle),
        ),
        const SizedBox(height: AppSpacing.sm),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: _AssetMasteryTile(item: item),
          ),
        ),
      ],
    );
  }
}

class _AssetMasteryTile extends StatelessWidget {
  const _AssetMasteryTile({required this.item});

  final LearningAssetMastery item;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(item.masteryStatus);
    final target = item.masteryStatus == 'needs_practice'
        ? '/review/speaking/${item.materialId}'
        : '/lessons/${item.materialId}';
    final card = AppCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: RemoteAssetImage(
              url: item.imageUrl,
              width: 64,
              height: 64,
              errorIcon: item.kind == 'sentence'
                  ? Icons.short_text_rounded
                  : Icons.image_outlined,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                        child: Text(item.text, style: AppTextStyles.cardTitle)),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.sm,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(_statusLabel(item.masteryStatus)),
                    ),
                  ],
                ),
                if (item.translation.isNotEmpty) ...<Widget>[
                  const SizedBox(height: AppSpacing.xs),
                  Text(item.translation, style: AppTextStyles.helper),
                ],
                const SizedBox(height: AppSpacing.sm),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    minHeight: 8,
                    value: (item.masteryScore / 100).clamp(0, 1),
                    backgroundColor: AppColors.softSheet,
                    color: color,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  '复习 ${item.completedReviewTasks}/${item.reviewAttempts} · 口语 ${item.speakingAttempts} 次',
                  style: AppTextStyles.helper,
                ),
                if (item.bestSpeakingScore != null)
                  Text('最佳口语 ${item.bestSpeakingScore!.round()} 分',
                      style: AppTextStyles.helper),
                if (item.weakPoints.isNotEmpty)
                  Text('需加强：${item.weakPoints.join('、')}',
                      style: AppTextStyles.helper),
                if (item.recommendedAction.isNotEmpty) ...<Widget>[
                  const SizedBox(height: AppSpacing.xs),
                  Text(item.recommendedAction),
                ],
              ],
            ),
          ),
        ],
      ),
    );
    return item.materialId.isEmpty
        ? card
        : InkWell(
            onTap: () => context.push(target),
            borderRadius: BorderRadius.circular(AppRadii.card),
            child: card,
          );
  }
}

class _RecommendedActions extends StatelessWidget {
  const _RecommendedActions({required this.items});

  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('推荐动作', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                children: <Widget>[
                  const Icon(Icons.auto_awesome_rounded,
                      color: AppColors.coralJam, size: 18),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(child: Text(item)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _statusLabel(String status) {
  return switch (status) {
    'mastered' => '已掌握',
    'progressing' => '练习中',
    _ => '需加强',
  };
}

Color _statusColor(String status) {
  return switch (status) {
    'mastered' => AppColors.mintLeaf,
    'progressing' => AppColors.butterYellow,
    _ => AppColors.coralJam,
  };
}
