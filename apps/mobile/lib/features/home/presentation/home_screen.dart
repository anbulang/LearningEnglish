import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_chip.dart';
import '../../profiles/data/demo_data.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    final materials = ref.watch(materialsProvider);
    final report = ref.watch(weeklyReportProvider);
    final tasks = ref.watch(reviewTasksProvider);
    final formFactor = formFactorOf(context);

    final dashboard = ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: <Widget>[
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('你好，今天继续陪 ${child.name} 复习', style: AppTextStyles.pageTitle),
              const SizedBox(height: AppSpacing.sm),
              Text('建议先完成 ${tasks.length} 个任务，控制在 ${child.preferredReviewDurationMinutes} 分钟内。'),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: <Widget>[
                  FilledButton.icon(
                    onPressed: () => context.go('/materials/scan'),
                    icon: const Icon(Icons.camera_alt_rounded),
                    label: const Text('上传讲义'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => context.go('/review/session/material_demo_1'),
                    icon: const Icon(Icons.play_circle_outline_rounded),
                    label: const Text('开始复习'),
                  ),
                  TextButton.icon(
                    onPressed: () => context.go('/review/coaching/material_demo_1'),
                    icon: const Icon(Icons.favorite_outline_rounded),
                    label: const Text('亲子陪练'),
                  ),
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
              Text('今日待复习', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              ...tasks.map(
                (task) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(task.contentJson['prompt'] as String? ?? '复习任务'),
                  subtitle: Text(task.taskType.value),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.go('/review/session/${task.materialId}'),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('最近课程', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              ...materials.map(
                (material) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(material.title),
                  subtitle: Text('${material.teacherName} · ${material.topic}'),
                  trailing: MaterialStatusChip(material.status),
                  onTap: () => context.go('/lessons/${material.id}'),
                ),
              ),
            ],
          ),
        ),
      ],
    );

    if (!formFactor.isFullTablet) {
      return Scaffold(appBar: AppBar(title: const Text('首页')), body: dashboard);
    }

    return Scaffold(
      appBar: AppBar(title: const Text('首页')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(flex: 2, child: dashboard),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                children: <Widget>[
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('本周进度', style: AppTextStyles.sectionTitle),
                        const SizedBox(height: AppSpacing.sm),
                        Text('已完成 ${report.completedSessions} 次复习'),
                        Text('复习单词 ${report.reviewedWords} 个'),
                        Text('口语尝试 ${report.speakingAttempts} 次'),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('本周薄弱点', style: AppTextStyles.sectionTitle),
                        const SizedBox(height: AppSpacing.sm),
                        ...report.weakItems.map((item) => Text('• $item')),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
