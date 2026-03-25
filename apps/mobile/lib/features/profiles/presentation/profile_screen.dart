import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/widgets/app_card.dart';
import '../data/demo_data.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('我的')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: <Widget>[
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
          const AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('家长偏好', style: AppTextStyles.cardTitle),
                SizedBox(height: AppSpacing.xs),
                Text('默认复习时长：10 分钟'),
                Text('孩子模式保护：PIN 已开启'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
