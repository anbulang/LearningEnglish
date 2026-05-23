import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../../core/widgets/status_chip.dart';
import '../../materials/data/app_repository.dart';
import '../../materials/presentation/material_navigation.dart';
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
            assetPath: AppIllustrations.stateEmpty,
            action: FilledButton(
              onPressed: () async {
                final created =
                    await ref.read(appRepositoryProvider).createChild(
                          name: 'Mia',
                          age: 6,
                          level: 'starter',
                          learningGoal: '课后复习更稳定',
                          preferredReviewDurationMinutes: 10,
                          parentNotes: '更喜欢看图认词',
                        );
                await ref
                    .read(sessionControllerProvider.notifier)
                    .addChild(created);
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
        IllustratedHeroCard(
          eyebrow: '今日陪学',
          title: '和 ${child.name} 一起把课堂讲义变成小课包',
          description: tasks.when(
            data: (items) =>
                '今天建议先完成 ${items.length} 个任务，控制在 ${child.preferredReviewDurationMinutes} 分钟内。',
            loading: () => '正在同步今天的复习任务...',
            error: (_, __) => '任务同步失败，请稍后重试。',
          ),
          accent: AppColors.coralJam,
          illustration: Icons.menu_book_rounded,
          assetPath: AppIllustrations.heroHome,
          badge: const StickerBadge(
              label: '轻松 10 分钟', icon: Icons.auto_awesome_rounded),
          actions: <Widget>[
            FilledButton.icon(
              onPressed: () => context.go('/materials/scan'),
              icon: const Icon(Icons.camera_alt_rounded),
              label: const Text('上传讲义'),
            ),
            OutlinedButton.icon(
              onPressed: () {
                final loadedMaterials = materials.valueOrNull;
                final readyMaterial = firstReadyMaterial(loadedMaterials);
                if (readyMaterial != null) {
                  context.go('/review/session/${readyMaterial.id}');
                } else if (loadedMaterials != null &&
                    loadedMaterials.isNotEmpty) {
                  context.go(materialDestination(loadedMaterials.first));
                } else {
                  context.go('/review');
                }
              },
              icon: const Icon(Icons.play_circle_outline_rounded),
              label: const Text('开始复习'),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Text('今日待复习', style: AppTextStyles.sectionTitle),
                  const SizedBox(width: AppSpacing.sm),
                  const StickerBadge(
                      label: '鼓励模式',
                      icon: Icons.favorite_rounded,
                      color: AppColors.mintLeaf),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              ...tasks.when(
                data: (items) => items
                    .map(
                      (task) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Container(
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
                        title: Text(
                            task.contentJson['prompt'] as String? ?? '复习任务'),
                        subtitle: Text(task.taskType.value),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () =>
                            context.go('/review/session/${task.materialId}'),
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
                      (material) => Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(AppRadii.card),
                          onTap: () =>
                              context.go(materialDestination(material)),
                          child: Row(
                            children: <Widget>[
                              LessonCoverThumbnail(
                                title: material.title,
                                subtitle: material.topic,
                                icon: _topicIcon(material.topic),
                                accent: _topicAccent(material.topic),
                                assetPath:
                                    AppIllustrations.topicFor(material.topic),
                              ),
                              const SizedBox(width: AppSpacing.md),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(material.title,
                                        style: AppTextStyles.cardTitle),
                                    const SizedBox(height: AppSpacing.xs),
                                    Text(
                                      '${material.teacherName} · ${material.topic}',
                                      style: AppTextStyles.body,
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              MaterialStatusChip(material.status),
                            ],
                          ),
                        ),
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
                            _metricRow('已完成复习', '${value.completedSessions} 次',
                                Icons.bookmark_added_rounded),
                            _metricRow('复习单词', '${value.reviewedWords} 个',
                                Icons.style_rounded),
                            _metricRow('口语尝试', '${value.speakingAttempts} 次',
                                Icons.mic_rounded),
                          ],
                          loading: () =>
                              const <Widget>[CircularProgressIndicator()],
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
                          data: (value) => value.weakItems
                              .map(
                                (item) => Padding(
                                  padding: const EdgeInsets.only(
                                      bottom: AppSpacing.sm),
                                  child: Container(
                                    padding:
                                        const EdgeInsets.all(AppSpacing.sm),
                                    decoration: BoxDecoration(
                                      color: AppColors.softSheet,
                                      borderRadius: BorderRadius.circular(18),
                                    ),
                                    child: Row(
                                      children: <Widget>[
                                        const Icon(Icons.push_pin_rounded,
                                            color: AppColors.coralJam),
                                        const SizedBox(width: AppSpacing.sm),
                                        Expanded(child: Text(item)),
                                      ],
                                    ),
                                  ),
                                ),
                              )
                              .toList(),
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

Widget _metricRow(String label, String value, IconData icon) {
  return Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: Row(
      children: <Widget>[
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: AppColors.mintLeaf.withValues(alpha: 0.28),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Icon(icon, color: AppColors.forestMint, size: 20),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(child: Text(label, style: AppTextStyles.body)),
        Text(value, style: AppTextStyles.cardTitle),
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

Color _topicAccent(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return AppColors.mintLeaf;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return AppColors.butterYellow;
  }
  return AppColors.skyBlue;
}

IconData _topicIcon(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return Icons.pets_rounded;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return Icons.looks_one_rounded;
  }
  return Icons.auto_stories_rounded;
}
