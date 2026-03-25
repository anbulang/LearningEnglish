import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import 'app_card.dart';

class StatePanel extends StatelessWidget {
  const StatePanel({
    required this.title,
    required this.description,
    super.key,
    this.icon = Icons.info_outline_rounded,
    this.action,
  });

  final Widget? action;
  final String description;
  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 40, color: AppColors.coralJam),
          const SizedBox(height: AppSpacing.sm),
          Text(title, style: AppTextStyles.sectionTitle, textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.xs),
          Text(description, textAlign: TextAlign.center),
          if (action != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            action!,
          ],
        ],
      ),
    );
  }
}
