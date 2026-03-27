import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
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
      final report = ref.watch(weeklyReportProvider);
      return Scaffold(
        appBar: AppBar(title: const Text('报告')),
        body: report.when(
          data: (value) => ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: <Widget>[
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('本周复习概览', style: AppTextStyles.pageTitle),
                    const SizedBox(height: AppSpacing.sm),
                    Text('完成 ${value.completedSessions} 次复习'),
                    Text('复习 ${value.reviewedWords} 个单词'),
                    Text('口语练习 ${value.speakingAttempts} 次'),
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
                    ...value.recommendedActions.map((item) => Text('• $item')),
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
              description: error.toString(),
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
                    Text(task.contentJson['prompt'] as String? ?? '复习任务', style: AppTextStyles.sectionTitle),
                    const SizedBox(height: AppSpacing.xs),
                    Text('类型：${task.taskType.value} · 难度：${task.difficulty}'),
                    const SizedBox(height: AppSpacing.md),
                    FilledButton(
                      onPressed: () => context.go('/review/session/${task.materialId}'),
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
            description: error.toString(),
          ),
        ),
      ),
    );
  }
}
