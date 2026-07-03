import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/no_child_state_panel.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';

class ReviewTasksScreen extends ConsumerWidget {
  const ReviewTasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    if (child == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('复习')),
        body: const Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: NoChildStatePanel(description: '复习需要先为孩子建立档案。'),
        ),
      );
    }

    final tasks = ref.watch(reviewTasksProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('复习')),
      body: tasks.when(
        data: (items) {
          if (items.isEmpty) {
            return Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: StatePanel(
                title: '今天没有待复习任务',
                description: '可以去资料库上传新讲义，或回到报告页查看本周进度。',
                assetPath: AppIllustrations.stateEmpty,
                action: FilledButton(
                  onPressed: () => context.go('/materials'),
                  child: const Text('去资料库'),
                ),
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
