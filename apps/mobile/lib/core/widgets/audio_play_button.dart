import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../audio/audio_player_controller.dart';

/// A tap-to-play control bound to the shared [audioPlaybackControllerProvider].
///
/// Pass an empty [url] to render a disabled control with [unavailableLabel] /
/// [unavailableTooltip] — used when TTS is still generating or failed. When
/// [label] is provided the control renders as a labelled button; otherwise it
/// is a compact icon button suited to cards and list tiles.
class AudioPlayButton extends ConsumerWidget {
  const AudioPlayButton({
    required this.url,
    this.label,
    this.tooltip = '播放标准音',
    this.unavailableTooltip = '发音生成中，暂不可播放',
    this.unavailableLabel = '发音生成中',
    this.enabled = true,
    this.iconSize = 22,
    super.key,
  });

  final String url;
  final String? label;
  final String tooltip;
  final String unavailableTooltip;
  final String unavailableLabel;

  /// When false the control is disabled even if [url] is set — e.g. while a
  /// recording is in progress, so playback can't fight the recorder's session.
  final bool enabled;
  final double iconSize;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasUrl = url.trim().isNotEmpty;
    final active = enabled && hasUrl;
    final state = ref.watch(audioPlaybackControllerProvider);
    final loading = active && state.isLoading(url);
    final playing = active && state.isPlaying(url);

    Future<void> handleTap() async {
      try {
        await ref.read(audioPlaybackControllerProvider.notifier).toggle(url);
      } catch (_) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('音频播放失败，请检查网络后重试。')),
          );
        }
      }
    }

    final spinner = SizedBox(
      width: iconSize - 4,
      height: iconSize - 4,
      child: const CircularProgressIndicator(strokeWidth: 2),
    );
    final glyph = playing ? Icons.stop_rounded : Icons.volume_up_rounded;
    final onPressed = active && !loading ? handleTap : null;

    if (label != null) {
      return OutlinedButton.icon(
        onPressed: onPressed,
        icon: loading ? spinner : Icon(glyph),
        label: Text(
          !hasUrl ? unavailableLabel : (playing ? '停止' : label!),
        ),
      );
    }

    return IconButton(
      onPressed: onPressed,
      tooltip: !hasUrl
          ? unavailableTooltip
          : (enabled ? tooltip : '录音时暂不可播放'),
      visualDensity: VisualDensity.compact,
      iconSize: iconSize,
      color: active ? AppColors.skyBlue : null,
      icon: loading ? spinner : Icon(glyph),
    );
  }
}
