import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
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
        body: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: <Widget>[
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('本周复习概览', style: AppTextStyles.pageTitle),
                  const SizedBox(height: AppSpacing.sm),
                  Text('完成 ${report.completedSessions} 次复习'),
                  Text('复习 ${report.reviewedWords} 个单词'),
                  Text('口语练习 ${report.speakingAttempts} 次'),
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
                  ...report.recommendedActions.map((item) => Text('• $item')),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final tasks = ref.watch(reviewTasksProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('复习')),
      body: ListView.separated(
        padding: const EdgeInsets.all(AppSpacing.md),
        itemBuilder: (context, index) {
          final task = tasks[index];
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
        itemCount: tasks.length,
      ),
    );
  }
}
