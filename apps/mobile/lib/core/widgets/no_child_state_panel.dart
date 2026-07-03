import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../assets/app_illustrations.dart';
import 'state_panel.dart';

/// Unified empty state shown wherever a feature needs an active child profile
/// (upload / review / speaking / reports / home). Gives one consistent
/// actionable path to the profile screen instead of five divergent dead-ends.
class NoChildStatePanel extends StatelessWidget {
  const NoChildStatePanel({this.description, super.key});

  final String? description;

  @override
  Widget build(BuildContext context) {
    return StatePanel(
      title: '先添加孩子档案',
      description: description ?? '上传讲义、复习、口语练习和周报都需要先为孩子建立档案。',
      icon: Icons.child_care_rounded,
      assetPath: AppIllustrations.stateEmpty,
      action: FilledButton.icon(
        onPressed: () => context.go('/profile'),
        icon: const Icon(Icons.person_add_alt_1_rounded),
        label: const Text('添加孩子档案'),
      ),
    );
  }
}
