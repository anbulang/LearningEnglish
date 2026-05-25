import 'dart:async';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

final speakingRecorderControllerProvider = AutoDisposeAsyncNotifierProvider<
    SpeakingRecorderController, SpeakingRecorderState>(
  SpeakingRecorderController.new,
);

class SpeakingRecorderState {
  const SpeakingRecorderState({
    this.isRecording = false,
    this.audioPath = '',
    this.durationMs = 0,
    this.errorMessage = '',
  });

  final String audioPath;
  final int durationMs;
  final String errorMessage;
  final bool isRecording;

  SpeakingRecorderState copyWith({
    String? audioPath,
    int? durationMs,
    String? errorMessage,
    bool? isRecording,
  }) {
    return SpeakingRecorderState(
      audioPath: audioPath ?? this.audioPath,
      durationMs: durationMs ?? this.durationMs,
      errorMessage: errorMessage ?? this.errorMessage,
      isRecording: isRecording ?? this.isRecording,
    );
  }
}

class SpeakingRecorderController
    extends AutoDisposeAsyncNotifier<SpeakingRecorderState> {
  final AudioRecorder _recorder = AudioRecorder();
  DateTime? _startedAt;

  @override
  FutureOr<SpeakingRecorderState> build() {
    ref.onDispose(_recorder.dispose);
    return const SpeakingRecorderState();
  }

  Future<void> start() async {
    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      state = const AsyncData(
        SpeakingRecorderState(errorMessage: '没有麦克风权限，请在系统设置中允许录音。'),
      );
      return;
    }
    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/speaking-${DateTime.now().millisecondsSinceEpoch}.m4a';
    _startedAt = DateTime.now();
    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        sampleRate: 16000,
        numChannels: 1,
      ),
      path: path,
    );
    state =
        AsyncData(SpeakingRecorderState(isRecording: true, audioPath: path));
  }

  Future<void> stop() async {
    final path = await _recorder.stop();
    final startedAt = _startedAt;
    final durationMs = startedAt == null
        ? 0
        : DateTime.now().difference(startedAt).inMilliseconds;
    state = AsyncData(
      SpeakingRecorderState(
        isRecording: false,
        audioPath: path ?? state.valueOrNull?.audioPath ?? '',
        durationMs: durationMs,
      ),
    );
  }

  Future<void> clear() async {
    final current = state.valueOrNull;
    if (current != null && current.audioPath.isNotEmpty) {
      final file = File(current.audioPath);
      if (await file.exists()) {
        await file.delete();
      }
    }
    state = const AsyncData(SpeakingRecorderState());
  }
}
