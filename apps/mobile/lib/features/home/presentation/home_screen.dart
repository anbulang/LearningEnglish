import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/state_panel.dart';
import '../../../core/widgets/status_chip.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';
import '../../session/data/session_controller.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    final materials = ref.watch(materialsProvider);
    final report = ref.watch(weeklyReportProvider);
    final tasks = ref.watch(reviewTasksProvider);
    final formFactor = formFactorOf(context);

    if (child == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('首页')),
        body: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: StatePanel(
            title: '还没有孩子档案',
            description: '先创建一个孩子档案，再开始上传讲义和生成复习包。',
            action: FilledButton(
              onPressed: () async {
                final created = await ref.read(appRepositoryProvider).createChild(
                      name: 'Mia',
                      age: 6,
                      level: 'starter',
                      learningGoal: '课后复习更稳定',
                      preferredReviewDurationMinutes: 10,
                      parentNotes: '更喜欢看图认词',
                    );
                await ref.read(sessionControllerProvider.notifier).addChild(created);
              },
              child: const Text('创建默认孩子档案'),
            ),
          ),
        ),
      );
    }

    final dashboard = ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: <Widget>[
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('你好，今天继续陪 ${child.name} 复习', style: AppTextStyles.pageTitle),
              const SizedBox(height: AppSpacing.sm),
              Text(
                tasks.when(
                  data: (items) => '建议先完成 ${items.length} 个任务，控制在 ${child.preferredReviewDurationMinutes} 分钟内。',
                  loading: () => '正在同步今天的复习任务...',
                  error: (_, __) => '任务同步失败，请稍后重试。',
                ),
              ),
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
                    onPressed: () {
                      final loadedMaterials = materials.valueOrNull;
                      final firstMaterial =
                          loadedMaterials != null && loadedMaterials.isNotEmpty ? loadedMaterials.first : null;
                      if (firstMaterial != null) {
                        context.go('/review/session/${firstMaterial.id}');
                      } else {
                        context.go('/review');
                      }
                    },
                    icon: const Icon(Icons.play_circle_outline_rounded),
                    label: const Text('开始复习'),
                  ),
                  TextButton.icon(
                    onPressed: () {
                      final loadedMaterials = materials.valueOrNull;
                      final firstMaterial =
                          loadedMaterials != null && loadedMaterials.isNotEmpty ? loadedMaterials.first : null;
                      if (firstMaterial != null) {
                        context.go('/review/coaching/${firstMaterial.id}');
                      }
                    },
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
              ...tasks.when(
                data: (items) => items
                    .map(
                      (task) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(task.contentJson['prompt'] as String? ?? '复习任务'),
                        subtitle: Text(task.taskType.value),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () => context.go('/review/session/${task.materialId}'),
                      ),
                    )
                    .toList(),
                loading: () => const <Widget>[
                  Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                ],
                error: (_, __) => const <Widget>[
                  Text('任务加载失败'),
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
              Text('最近课程', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              ...materials.when(
                data: (items) => items
                    .map(
                      (material) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(material.title),
                        subtitle: Text('${material.teacherName} · ${material.topic}'),
                        trailing: MaterialStatusChip(material.status),
                        onTap: () => context.go('/lessons/${material.id}'),
                      ),
                    )
                    .toList(),
                loading: () => const <Widget>[
                  Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                ],
                error: (_, __) => const <Widget>[
                  Text('课程加载失败'),
                ],
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
                            ...report.when(
                              data: (value) => <Widget>[
                                Text('已完成 ${value.completedSessions} 次复习'),
                                Text('复习单词 ${value.reviewedWords} 个'),
                                Text('口语尝试 ${value.speakingAttempts} 次'),
                              ],
                              loading: () => const <Widget>[CircularProgressIndicator()],
                              error: (_, __) => const <Widget>[Text('报告加载失败')],
                            ),
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
                          ...report.when(
                            data: (value) => value.weakItems.map((item) => Text('• $item')).toList(),
                            loading: () => const <Widget>[Text('正在汇总...')],
                            error: (_, __) => const <Widget>[Text('暂无数据')],
                          ),
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
