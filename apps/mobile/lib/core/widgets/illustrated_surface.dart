import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

class IllustratedHeroCard extends StatelessWidget {
  const IllustratedHeroCard({
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.accent,
    required this.illustration,
    super.key,
    this.assetPath,
    this.badge,
    this.actions = const <Widget>[],
  });

  final Color accent;
  final List<Widget> actions;
  final String? assetPath;
  final Widget? badge;
  final String description;
  final String eyebrow;
  final IconData illustration;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: <Color>[
            AppColors.paperWhite,
            Color.alphaBlend(
                accent.withValues(alpha: 0.16), AppColors.softSheet),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppRadii.panel),
        boxShadow: AppShadows.card,
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: -24,
            right: -8,
            child: _Blob(size: 132, color: accent.withValues(alpha: 0.18)),
          ),
          Positioned(
            bottom: -28,
            right: 48,
            child: _Blob(
                size: 92,
                color: AppColors.butterYellow.withValues(alpha: 0.24)),
          ),
          Positioned(
            top: 26,
            right: 18,
            child: _IllustrationStamp(
              icon: illustration,
              accent: accent,
              assetPath: assetPath,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.sm,
                        vertical: AppSpacing.xs,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.paperWhite.withValues(alpha: 0.88),
                        borderRadius: BorderRadius.circular(AppRadii.pill),
                      ),
                      child: Text(eyebrow, style: AppTextStyles.eyebrow),
                    ),
                    if (badge != null) ...<Widget>[
                      const SizedBox(width: AppSpacing.sm),
                      badge!,
                    ],
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 260),
                  child: Text(title, style: AppTextStyles.heroTitle),
                ),
                const SizedBox(height: AppSpacing.sm),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 320),
                  child: Text(description, style: AppTextStyles.body),
                ),
                if (actions.isNotEmpty) ...<Widget>[
                  const SizedBox(height: AppSpacing.lg),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: actions,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class LessonCoverThumbnail extends StatelessWidget {
  const LessonCoverThumbnail({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    super.key,
    this.assetPath,
  });

  final Color accent;
  final String? assetPath;
  final IconData icon;
  final String subtitle;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 92,
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: <Color>[
            Color.alphaBlend(
                accent.withValues(alpha: 0.24), AppColors.paperWhite),
            AppColors.paperWhite,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
        borderRadius: BorderRadius.circular(AppRadii.card),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Container(
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(18),
              ),
              child: assetPath == null
                  ? Center(
                      child: Icon(icon, color: AppColors.cocoaCoral, size: 28),
                    )
                  : Image.asset(
                      assetPath!,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Center(
                        child:
                            Icon(icon, color: AppColors.cocoaCoral, size: 28),
                      ),
                    ),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(title,
              style: AppTextStyles.cardTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
          const SizedBox(height: AppSpacing.xxs),
          Text(subtitle,
              style: AppTextStyles.helper,
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

class StickerBadge extends StatelessWidget {
  const StickerBadge({
    required this.label,
    super.key,
    this.color = AppColors.butterYellow,
    this.textColor = AppColors.inkCocoa,
    this.icon,
  });

  final Color color;
  final IconData? icon;
  final String label;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Transform.rotate(
      angle: -0.06,
      child: Container(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(AppRadii.pill),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (icon != null) ...<Widget>[
              Icon(icon, size: 14, color: textColor),
              const SizedBox(width: AppSpacing.xs),
            ],
            Text(
              label,
              style: AppTextStyles.helper
                  .copyWith(color: textColor, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }
}

class _IllustrationStamp extends StatelessWidget {
  const _IllustrationStamp({
    required this.icon,
    required this.accent,
    this.assetPath,
  });

  final Color accent;
  final String? assetPath;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 112,
      height: 112,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.paperWhite.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(34),
      ),
      child: assetPath == null
          ? _FallbackStampIcon(icon: icon, accent: accent)
          : Image.asset(
              assetPath!,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                  _FallbackStampIcon(icon: icon, accent: accent),
            ),
    );
  }
}

class _FallbackStampIcon extends StatelessWidget {
  const _FallbackStampIcon({
    required this.icon,
    required this.accent,
  });

  final Color accent;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: <Widget>[
        Positioned(
          top: 18,
          child:
              Icon(Icons.auto_awesome, color: AppColors.butterYellow, size: 18),
        ),
        Icon(icon, color: accent, size: 52),
        Positioned(
          bottom: 16,
          right: 20,
          child: Icon(Icons.star_rounded,
              color: AppColors.coralJam.withValues(alpha: 0.88), size: 16),
        ),
      ],
    );
  }
}

class _Blob extends StatelessWidget {
  const _Blob({
    required this.size,
    required this.color,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(size * 0.42),
      ),
    );
  }
}
