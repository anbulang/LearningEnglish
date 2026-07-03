import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';

/// Playback phase for the single shared audio player.
enum AudioPhase { idle, loading, playing }

/// Tracks which URL (if any) is currently being played and its phase, so every
/// [AudioPlayButton] in the tree can reflect the right state and only one clip
/// plays at a time.
class AudioPlaybackState {
  const AudioPlaybackState({this.activeUrl, this.phase = AudioPhase.idle});

  final String? activeUrl;
  final AudioPhase phase;

  bool isLoading(String url) => activeUrl == url && phase == AudioPhase.loading;
  bool isPlaying(String url) => activeUrl == url && phase == AudioPhase.playing;
  bool isActive(String url) => activeUrl == url && phase != AudioPhase.idle;
}

final audioPlaybackControllerProvider =
    StateNotifierProvider<AudioPlaybackController, AudioPlaybackState>((ref) {
  // The StateNotifier is disposed automatically when the provider is destroyed;
  // its overridden dispose() releases the underlying player.
  return AudioPlaybackController();
});

/// Wraps a single [AudioPlayer]. The underlying player is created lazily on the
/// first [toggle] call so that merely rendering an [AudioPlayButton] never
/// touches the platform plugin (keeps widget tests free of audio plugins).
class AudioPlaybackController extends StateNotifier<AudioPlaybackState> {
  AudioPlaybackController() : super(const AudioPlaybackState());

  AudioPlayer? _player;
  String? _pendingUrl;

  AudioPlayer _ensurePlayer() {
    final existing = _player;
    if (existing != null) {
      return existing;
    }
    final player = AudioPlayer();
    player.playerStateStream.listen(_onPlayerState);
    _player = player;
    return player;
  }

  void _onPlayerState(PlayerState playerState) {
    if (!mounted) {
      return;
    }
    final url = state.activeUrl;
    final processing = playerState.processingState;
    if (processing == ProcessingState.completed) {
      unawaited(_player?.stop());
      state = const AudioPlaybackState();
      return;
    }
    if (url == null) {
      return;
    }
    if (processing == ProcessingState.loading ||
        processing == ProcessingState.buffering) {
      state = AudioPlaybackState(activeUrl: url, phase: AudioPhase.loading);
    } else if (playerState.playing) {
      state = AudioPlaybackState(activeUrl: url, phase: AudioPhase.playing);
    }
  }

  /// Plays [url], or stops if [url] is already the active clip. Throws on load
  /// failure so callers can surface a message.
  Future<void> toggle(String url) async {
    final target = url.trim();
    if (target.isEmpty) {
      return;
    }
    final player = _ensurePlayer();
    if (state.isActive(target)) {
      _pendingUrl = null;
      await player.stop();
      state = const AudioPlaybackState();
      return;
    }
    _pendingUrl = target;
    state = AudioPlaybackState(activeUrl: target, phase: AudioPhase.loading);
    try {
      await player.stop();
      await player.setUrl(target);
      if (!mounted || _pendingUrl != target) {
        return;
      }
      unawaited(player.play());
    } catch (_) {
      if (mounted && state.activeUrl == target) {
        state = const AudioPlaybackState();
      }
      rethrow;
    }
  }

  /// Stops any current playback (used to hand the audio session back to the
  /// recorder, or when leaving a screen).
  Future<void> stop() async {
    _pendingUrl = null;
    final player = _player;
    if (player == null) {
      return;
    }
    await player.stop();
    if (mounted) {
      state = const AudioPlaybackState();
    }
  }

  @override
  void dispose() {
    _player?.dispose();
    super.dispose();
  }
}
