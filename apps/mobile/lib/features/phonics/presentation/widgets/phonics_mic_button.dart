import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

/// A big circular tap-to-record button sized for small hands. Tapping toggles
/// between [onStart] and [onStop] based on [isRecording]. Disabled (greyed) when
/// [enabled] is false — e.g. while an attempt is uploading/scoring.
class PhonicsMicButton extends StatelessWidget {
  const PhonicsMicButton({
    required this.isRecording,
    required this.enabled,
    required this.onStart,
    required this.onStop,
    super.key,
    this.size = 116,
  });

  final bool enabled;
  final bool isRecording;
  final VoidCallback onStart;
  final VoidCallback onStop;
  final double size;

  @override
  Widget build(BuildContext context) {
    final active = enabled;
    final Color circleColor = !active
        ? AppColors.outlineVariant
        : (isRecording ? AppColors.coralJam : AppColors.skyBlue);
    final label = isRecording ? '停止录音' : '点我录音';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Semantics(
          button: true,
          enabled: active,
          label: label,
          child: Material(
            color: Colors.transparent,
            shape: const CircleBorder(),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: !active ? null : (isRecording ? onStop : onStart),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: size,
                height: size,
                decoration: BoxDecoration(
                  color: circleColor,
                  shape: BoxShape.circle,
                  boxShadow: active ? AppShadows.card : null,
                ),
                child: Icon(
                  isRecording ? Icons.stop_rounded : Icons.mic_rounded,
                  size: size * 0.42,
                  color: active ? AppColors.cocoaCoral : AppColors.paperWhite,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(label, style: AppTextStyles.helper),
      ],
    );
  }
}
