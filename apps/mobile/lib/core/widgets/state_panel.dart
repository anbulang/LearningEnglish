import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import 'app_card.dart';

class StatePanel extends StatelessWidget {
  const StatePanel({
    required this.title,
    required this.description,
    super.key,
    this.icon = Icons.info_outline_rounded,
    this.assetPath,
    this.action,
  });

  final Widget? action;
  final String? assetPath;
  final String description;
  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _StateVisual(icon: icon, assetPath: assetPath),
          const SizedBox(height: AppSpacing.sm),
          Text(title,
              style: AppTextStyles.sectionTitle, textAlign: TextAlign.center),
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

class _StateVisual extends StatelessWidget {
  const _StateVisual({
    required this.icon,
    this.assetPath,
  });

  final String? assetPath;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    if (assetPath == null) {
      return Icon(icon, size: 40, color: AppColors.coralJam);
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: Image.asset(
        assetPath!,
        width: 112,
        height: 112,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) =>
            Icon(icon, size: 40, color: AppColors.coralJam),
      ),
    );
  }
}
