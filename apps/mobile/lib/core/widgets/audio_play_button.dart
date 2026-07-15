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
    // The controller stores the trimmed URL as activeUrl, so match against the
    // trimmed value (a raw url with stray whitespace would never appear active).
    final trimmed = url.trim();
    final hasUrl = trimmed.isNotEmpty;
    final active = enabled && hasUrl;
    // Watch only THIS clip's (loading, playing) via select, so one tap rebuilds
    // just the active / previously-active button instead of every AudioPlayButton
    // on a scroll-heavy page.
    final playback = ref.watch(
      audioPlaybackControllerProvider.select(
        (s) => (loading: s.isLoading(trimmed), playing: s.isPlaying(trimmed)),
      ),
    );
    final loading = active && playback.loading;
    final playing = active && playback.playing;

    Future<void> handleTap() async {
      try {
        await ref
            .read(audioPlaybackControllerProvider.notifier)
            .toggle(trimmed);
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
        // Reflect the recording-disabled reason (mirrors the icon variant's
        // tooltip) instead of showing the normal label greyed with no cue.
        label: Text(
          !hasUrl
              ? unavailableLabel
              : !enabled
                  ? '录音时暂不可播放'
                  : (playing ? '停止' : label!),
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
