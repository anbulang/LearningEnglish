import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

/// Visual feedback state for a [PhonicsLetterTile].
enum PhonicsTileState { idle, selected, correct, incorrect }

/// A big, kid-friendly tappable letter tile. Used both for圈首音 choice
/// options (with [state] driving ✓/✗ feedback) and for blending segments
/// (with a small speaker glyph, since tapping plays that letter's sound).
class PhonicsLetterTile extends StatelessWidget {
  const PhonicsLetterTile({
    required this.letter,
    super.key,
    this.state = PhonicsTileState.idle,
    this.onTap,
    this.showSpeaker = false,
    this.size = 76,
  });

  final String letter;
  final VoidCallback? onTap;
  final bool showSpeaker;
  final double size;
  final PhonicsTileState state;

  @override
  Widget build(BuildContext context) {
    final palette = _paletteFor(state);
    return Semantics(
      button: onTap != null,
      label: '字母 $letter',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadii.card),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: palette.fill,
              borderRadius: BorderRadius.circular(AppRadii.card),
              border: Border.all(color: palette.border, width: 2),
            ),
            child: Stack(
              alignment: Alignment.center,
              children: <Widget>[
                Text(
                  letter,
                  style: AppTextStyles.heroTitle.copyWith(
                    fontSize: size * 0.44,
                    color: palette.text,
                  ),
                ),
                if (showSpeaker)
                  Positioned(
                    bottom: 6,
                    right: 6,
                    child: Icon(Icons.volume_up_rounded,
                        size: 16, color: palette.text.withValues(alpha: 0.7)),
                  ),
                if (state == PhonicsTileState.correct)
                  const Positioned(
                    top: 4,
                    right: 4,
                    child: Icon(Icons.check_circle_rounded,
                        size: 20, color: AppColors.forestMint),
                  ),
                if (state == PhonicsTileState.incorrect)
                  const Positioned(
                    top: 4,
                    right: 4,
                    child: Icon(Icons.cancel_rounded,
                        size: 20, color: AppColors.coralJam),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  _TilePalette _paletteFor(PhonicsTileState state) {
    switch (state) {
      case PhonicsTileState.idle:
        return const _TilePalette(
          fill: AppColors.paperWhite,
          border: AppColors.outlineVariant,
          text: AppColors.inkCocoa,
        );
      case PhonicsTileState.selected:
        return const _TilePalette(
          fill: AppColors.skyBlue,
          border: AppColors.skyBlue,
          text: AppColors.inkCocoa,
        );
      case PhonicsTileState.correct:
        return const _TilePalette(
          fill: AppColors.successSurface,
          border: AppColors.forestMint,
          text: AppColors.forestMint,
        );
      case PhonicsTileState.incorrect:
        return const _TilePalette(
          fill: AppColors.errorSurface,
          border: AppColors.coralJam,
          text: AppColors.cocoaCoral,
        );
    }
  }
}

class _TilePalette {
  const _TilePalette({
    required this.fill,
    required this.border,
    required this.text,
  });

  final Color border;
  final Color fill;
  final Color text;
}
