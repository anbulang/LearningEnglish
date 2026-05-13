import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../data/demo_data.dart';
import '../../session/data/session_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final child = ref.watch(activeChildProvider);
    final parent = ref.watch(currentParentProvider);
    final session = child == null ? null : ref.watch(sessionControllerProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('我的')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: <Widget>[
          IllustratedHeroCard(
            eyebrow: '家庭档案',
            title: child == null ? '管理家庭学习档案' : '${child.name} 的学习小档案',
            description: child == null
                ? '先添加孩子档案，后续上传讲义、AI 校对、复习报告都会按孩子独立归档。'
                : '这里管理家长账号、孩子资料、学习目标和提醒偏好，保持整套课后复习节奏稳定。',
            accent: AppColors.coralJam,
            illustration: Icons.family_restroom_rounded,
            assetPath: AppIllustrations.topicFamily,
            badge: StickerBadge(
              label: child?.level ?? '待添加',
              icon: child == null
                  ? Icons.person_add_alt_1_rounded
                  : Icons.star_rounded,
              color: AppColors.butterYellow,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                    parent?.displayName.isNotEmpty == true
                        ? parent!.displayName
                        : '家长账号',
                    style: AppTextStyles.sectionTitle),
                const SizedBox(height: AppSpacing.xs),
                Text(parent?.phoneNumber.isNotEmpty == true
                    ? parent!.phoneNumber
                    : '未绑定手机号'),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          if (child == null)
            StatePanel(
              title: '先添加孩子档案',
              description: '填写孩子姓名、年龄、英语水平和复习目标后，就可以上传讲义并生成报告。',
              assetPath: AppIllustrations.stateEmpty,
              action: FilledButton.icon(
                onPressed: () => _showAddChildSheet(context, ref),
                icon: const Icon(Icons.person_add_alt_1_rounded),
                label: const Text('添加孩子档案'),
              ),
            )
          else ...<Widget>[
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
                  if (session != null &&
                      session.children.length > 1) ...<Widget>[
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
                              onSelected: (_) => ref
                                  .read(sessionControllerProvider.notifier)
                                  .selectChild(item.id),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  FilledButton(
                    onPressed: () =>
                        ref.read(sessionControllerProvider.notifier).logout(),
                    child: const Text('退出登录'),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

Future<void> _showAddChildSheet(BuildContext context, WidgetRef ref) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => _AddChildSheet(ref: ref),
  );
}

class _AddChildSheet extends StatefulWidget {
  const _AddChildSheet({required this.ref});

  final WidgetRef ref;

  @override
  State<_AddChildSheet> createState() => _AddChildSheetState();
}

class _AddChildSheetState extends State<_AddChildSheet> {
  final _nameController = TextEditingController();
  final _ageController = TextEditingController(text: '6');
  final _levelController = TextEditingController(text: 'starter');
  final _goalController = TextEditingController(text: '课后复习更稳定');
  var _isSaving = false;

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _levelController.dispose();
    _goalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.md,
          right: AppSpacing.md,
          top: AppSpacing.md,
          bottom: MediaQuery.viewInsetsOf(context).bottom + AppSpacing.md,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('添加孩子档案', style: AppTextStyles.sectionTitle),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: _nameController,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: '孩子姓名'),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              controller: _ageController,
              keyboardType: TextInputType.number,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: '年龄'),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              controller: _levelController,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: '当前水平'),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              controller: _goalController,
              minLines: 2,
              maxLines: 3,
              decoration: const InputDecoration(labelText: '学习目标'),
            ),
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _isSaving ? null : _save,
                child: Text(_isSaving ? '保存中' : '保存档案'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请填写孩子姓名')),
      );
      return;
    }
    setState(() => _isSaving = true);
    try {
      final child = await widget.ref.read(appRepositoryProvider).createChild(
            name: name,
            age: int.tryParse(_ageController.text.trim()) ?? 6,
            level: _levelController.text.trim().isEmpty
                ? 'starter'
                : _levelController.text.trim(),
            learningGoal: _goalController.text.trim().isEmpty
                ? '课后复习更稳定'
                : _goalController.text.trim(),
            preferredReviewDurationMinutes: 10,
            parentNotes: '',
          );
      await widget.ref.read(sessionControllerProvider.notifier).addChild(child);
      widget.ref.invalidate(activeChildProvider);
      widget.ref.invalidate(weeklyReportProvider);
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('孩子档案保存失败，请稍后重试')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }
}
