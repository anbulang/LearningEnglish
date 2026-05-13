import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';

class ReviewTasksScreen extends ConsumerWidget {
  const ReviewTasksScreen({
    super.key,
    this.reportMode = false,
  });

  final bool reportMode;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (reportMode) {
      final child = ref.watch(activeChildProvider);
      if (child == null) {
        return Scaffold(
          appBar: AppBar(title: const Text('报告')),
          body: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: StatePanel(
              title: '先添加孩子档案',
              description: '添加孩子姓名、年龄和学习目标后，系统会开始生成每周复习报告。',
              assetPath: AppIllustrations.stateEmpty,
              action: FilledButton.icon(
                onPressed: () => context.go('/profile'),
                icon: const Icon(Icons.person_add_alt_1_rounded),
                label: const Text('去我的页面添加'),
              ),
            ),
          ),
        );
      }
      final report = ref.watch(weeklyReportProvider);
      return Scaffold(
        appBar: AppBar(title: const Text('报告')),
        body: report.when(
          data: (value) => ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: <Widget>[
              IllustratedHeroCard(
                eyebrow: '成长报告',
                title: '这周的学习树又长高了一点',
                description:
                    '完成 ${value.completedSessions} 次复习，复习 ${value.reviewedWords} 个单词，口语练习 ${value.speakingAttempts} 次。',
                accent: AppColors.mintLeaf,
                illustration: Icons.park_rounded,
                assetPath: AppIllustrations.heroWeeklyGrowth,
                badge: const StickerBadge(
                    label: '连续复习中', icon: Icons.workspace_premium_rounded),
              ),
              const SizedBox(height: AppSpacing.md),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('本周亮点', style: AppTextStyles.sectionTitle),
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: <Widget>[
                        _metricTile('完成复习', '${value.completedSessions}',
                            Icons.book_rounded, AppColors.skyBlue),
                        _metricTile('单词复习', '${value.reviewedWords}',
                            Icons.style_rounded, AppColors.butterYellow),
                        _metricTile('口语练习', '${value.speakingAttempts}',
                            Icons.mic_rounded, AppColors.mintLeaf),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('推荐动作', style: AppTextStyles.sectionTitle),
                    const SizedBox(height: AppSpacing.sm),
                    ...value.recommendedActions.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Container(
                          padding: const EdgeInsets.all(AppSpacing.sm),
                          decoration: BoxDecoration(
                            color: AppColors.softSheet,
                            borderRadius: BorderRadius.circular(18),
                          ),
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
                    ),
                  ],
                ),
              ),
            ],
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: StatePanel(
              title: '报告加载失败',
              description: describeApiError(error, fallback: '报告暂时不可用，请稍后重试。'),
              assetPath: AppIllustrations.stateError,
              action: FilledButton(
                onPressed: () => ref.invalidate(weeklyReportProvider),
                child: const Text('刷新报告'),
              ),
            ),
          ),
        ),
      );
    }

    final tasks = ref.watch(reviewTasksProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('复习')),
      body: tasks.when(
        data: (items) {
          if (items.isEmpty) {
            return const Padding(
              padding: EdgeInsets.all(AppSpacing.md),
              child: StatePanel(
                title: '今天没有待复习任务',
                description: '可以去资料库上传新讲义，或者回到报告页查看本周进度。',
                assetPath: AppIllustrations.stateEmpty,
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(AppSpacing.md),
            itemBuilder: (context, index) {
              final task = items[index];
              return AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: _taskAccent(task.taskType.value)
                                .withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Icon(_taskIcon(task.taskType.value),
                              color: AppColors.cocoaCoral),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: Text(
                            task.contentJson['prompt'] as String? ?? '复习任务',
                            style: AppTextStyles.sectionTitle,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text('类型：${task.taskType.value} · 难度：${task.difficulty}'),
                    const SizedBox(height: AppSpacing.md),
                    FilledButton(
                      onPressed: () =>
                          context.go('/review/session/${task.materialId}'),
                      child: const Text('开始任务'),
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
            itemCount: items.length,
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: StatePanel(
            title: '复习任务加载失败',
            description: describeApiError(error, fallback: '复习任务暂时不可用，请稍后重试。'),
            assetPath: AppIllustrations.stateError,
            action: FilledButton(
              onPressed: () => ref.invalidate(reviewTasksProvider),
              child: const Text('重新加载'),
            ),
          ),
        ),
      ),
    );
  }
}

Widget _metricTile(String label, String value, IconData icon, Color accent) {
  return Container(
    width: 150,
    padding: const EdgeInsets.all(AppSpacing.md),
    decoration: BoxDecoration(
      color: Color.alphaBlend(
          accent.withValues(alpha: 0.18), AppColors.paperWhite),
      borderRadius: BorderRadius.circular(AppRadii.card),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, color: AppColors.cocoaCoral),
        const SizedBox(height: AppSpacing.sm),
        Text(value, style: AppTextStyles.pageTitle),
        Text(label, style: AppTextStyles.helper),
      ],
    ),
  );
}

Color _taskAccent(String taskType) {
  if (taskType.contains('listen')) return AppColors.skyBlue;
  if (taskType.contains('match')) return AppColors.butterYellow;
  return AppColors.mintLeaf;
}

IconData _taskIcon(String taskType) {
  if (taskType.contains('listen')) return Icons.headphones_rounded;
  if (taskType.contains('match')) return Icons.extension_rounded;
  return Icons.style_rounded;
}
