import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
import '../data/demo_data.dart';
import '../../session/data/session_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    final parent = ref.watch(currentParentProvider);
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('我的')),
      body: child == null
          ? const Center(child: Text('暂无孩子档案'))
          : ListView(
              padding: const EdgeInsets.all(AppSpacing.md),
              children: <Widget>[
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(parent?.displayName ?? '家长账号', style: AppTextStyles.sectionTitle),
                      const SizedBox(height: AppSpacing.xs),
                      Text(parent?.phoneNumber ?? '未绑定手机号'),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(child.name, style: AppTextStyles.sectionTitle),
                      const SizedBox(height: AppSpacing.xs),
                      Text('年龄 ${child.age} 岁 · 当前水平 ${child.level}'),
                      const SizedBox(height: AppSpacing.md),
                      Text('学习目标：${child.learningGoal}'),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Text('家长偏好', style: AppTextStyles.cardTitle),
                      const SizedBox(height: AppSpacing.xs),
                      Text('默认复习时长：${child.preferredReviewDurationMinutes} 分钟'),
                      const Text('孩子模式保护：PIN 待接入'),
                      if (session.children.length > 1) ...<Widget>[
                        const SizedBox(height: AppSpacing.md),
                        const Text('切换孩子'),
                        const SizedBox(height: AppSpacing.xs),
                        Wrap(
                          spacing: AppSpacing.xs,
                          children: session.children
                              .map(
                                (item) => ChoiceChip(
                                  label: Text(item.name),
                                  selected: item.id == session.currentChildId,
                                  onSelected: (_) => ref.read(sessionControllerProvider.notifier).selectChild(item.id),
                                ),
                              )
                              .toList(),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.md),
                      FilledButton(
                        onPressed: () => ref.read(sessionControllerProvider.notifier).logout(),
                        child: const Text('退出登录'),
                      ),
                    ],
                  ),
                ),
              ],
      ),
    );
  }
}
