import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';
import '../data/speaking_recorder_controller.dart';

class SpeakingPartnerScreen extends ConsumerStatefulWidget {
  const SpeakingPartnerScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  ConsumerState<SpeakingPartnerScreen> createState() =>
      _SpeakingPartnerScreenState();
}

class _SpeakingPartnerScreenState extends ConsumerState<SpeakingPartnerScreen> {
  Timer? _pollTimer;
  String? _pollingStoppedAttemptId;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);
    final attempt = ref.watch(lastSpeakingAttemptProvider);
    final child = ref.watch(activeChildProvider);
    final materialAsync = ref.watch(materialProvider(widget.materialId));
    final material = materialAsync.valueOrNull;
    final recorderAsync = ref.watch(speakingRecorderControllerProvider);
    final recorder = recorderAsync.valueOrNull ?? const SpeakingRecorderState();
    final targetText = _targetText(material);
    _syncPolling(attempt);

    final stage = AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          IllustratedHeroCard(
            eyebrow: 'AI 口语陪练',
            title: targetText,
            description: '先录一遍孩子的跟读，再提交给 AI 生成转写、发音评分和逐词建议。',
            accent: AppColors.skyBlue,
            illustration: Icons.record_voice_over_rounded,
            assetPath: AppIllustrations.heroSpeakingPartner,
            badge: const StickerBadge(
              label: '开口说一说',
              icon: Icons.mic_rounded,
              color: AppColors.skyBlue,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          if (materialAsync.isLoading)
            const Text('正在读取课程内容...')
          else
            Text('跟读内容：$targetText'),
          const SizedBox(height: AppSpacing.md),
          Container(
            height: 180,
            decoration: BoxDecoration(
              color: AppColors.skyBlue.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(AppRadii.panel),
            ),
            clipBehavior: Clip.antiAlias,
            child: Image.asset(
              AppIllustrations.heroSpeakingPartner,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const Center(
                child: Icon(
                  Icons.record_voice_over_rounded,
                  size: 72,
                  color: AppColors.cocoaCoral,
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          _RecordingActions(
            recorder: recorder,
            isBusy: _isSubmitting ||
                recorderAsync.isLoading ||
                _isAttemptProcessing(attempt),
            onStart: _startRecording,
            onStop: _stopRecording,
            onClear: _clearRecording,
            onSubmit: child == null
                ? null
                : () => _submitAttempt(
                      child: child,
                      recorder: recorder,
                      targetText: targetText,
                    ),
          ),
          if (recorder.errorMessage.isNotEmpty ||
              _errorMessage != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Text(
              recorder.errorMessage.isNotEmpty
                  ? recorder.errorMessage
                  : _errorMessage!,
              style: const TextStyle(color: AppColors.coralJam),
            ),
          ],
        ],
      ),
    );

    final result = _AttemptResult(
      attempt: attempt,
      onRetry: attempt == null ? null : () => _retryAttempt(attempt.id),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('口语陪练')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: child == null
            ? const StatePanel(
                title: '缺少孩子档案',
                description: '请先完成家长账号初始化。',
                assetPath: AppIllustrations.stateEmpty,
              )
            : formFactor.isTablet
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(child: SingleChildScrollView(child: stage)),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(child: SingleChildScrollView(child: result)),
                    ],
                  )
                : ListView(
                    children: <Widget>[
                      stage,
                      const SizedBox(height: AppSpacing.md),
                      result,
                    ],
                  ),
      ),
    );
  }

  Future<void> _startRecording() async {
    try {
      await ref.read(speakingRecorderControllerProvider.notifier).start();
      setState(() => _errorMessage = null);
    } catch (error) {
      setState(() {
        _errorMessage = describeApiError(error, fallback: '录音启动失败，请检查麦克风权限。');
      });
    }
  }

  Future<void> _stopRecording() async {
    try {
      await ref.read(speakingRecorderControllerProvider.notifier).stop();
      setState(() => _errorMessage = null);
    } catch (error) {
      setState(() {
        _errorMessage = describeApiError(error, fallback: '录音保存失败，请重新录一次。');
      });
    }
  }

  Future<void> _clearRecording() async {
    final recorder = ref.read(speakingRecorderControllerProvider).valueOrNull;
    if (recorder?.isRecording == true) {
      setState(() => _errorMessage = '请先停止录音，再清除录音。');
      return;
    }
    await ref.read(speakingRecorderControllerProvider.notifier).clear();
    ref.read(lastSpeakingAttemptProvider.notifier).state = null;
    _pollTimer?.cancel();
    _pollingStoppedAttemptId = null;
    setState(() => _errorMessage = null);
  }

  Future<void> _submitAttempt({
    required ChildProfile child,
    required SpeakingRecorderState recorder,
    required String targetText,
  }) async {
    if (recorder.audioPath.isEmpty) {
      setState(() => _errorMessage = '请先录一段跟读音频。');
      return;
    }
    if (recorder.isRecording) {
      setState(() => _errorMessage = '请先停止录音，再提交评分。');
      return;
    }
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
      _pollingStoppedAttemptId = null;
    });
    try {
      final created =
          await ref.read(appRepositoryProvider).uploadSpeakingAttempt(
                childId: child.id,
                materialId: widget.materialId,
                promptText: '跟读：$targetText',
                targetText: targetText,
                audioPath: recorder.audioPath,
                audioDurationMs: recorder.durationMs,
              );
      if (!mounted) {
        return;
      }
      ref.read(lastSpeakingAttemptProvider.notifier).state = created;
      ref.read(appAnalyticsProvider).track('speaking_attempt_submitted', {
        'materialId': widget.materialId,
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = describeApiError(error, fallback: '口语提交失败，请稍后重试。');
      });
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _retryAttempt(String attemptId) async {
    setState(() {
      _errorMessage = null;
      _pollingStoppedAttemptId = null;
    });
    try {
      final retried =
          await ref.read(appRepositoryProvider).retrySpeakingAttempt(attemptId);
      if (!mounted) {
        return;
      }
      ref.read(lastSpeakingAttemptProvider.notifier).state = retried;
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = describeApiError(error, fallback: '重新评分失败，请稍后重试。');
      });
    }
  }

  void _syncPolling(SpeakingAttempt? attempt) {
    if (!_isAttemptProcessing(attempt)) {
      _pollTimer?.cancel();
      _pollTimer = null;
      _pollingStoppedAttemptId = null;
      return;
    }
    if (_pollingStoppedAttemptId == attempt?.id) {
      _pollTimer?.cancel();
      _pollTimer = null;
      return;
    }
    _pollTimer ??= Timer.periodic(const Duration(seconds: 3), (_) async {
      final current = ref.read(lastSpeakingAttemptProvider);
      if (!_isAttemptProcessing(current)) {
        _pollTimer?.cancel();
        _pollTimer = null;
        return;
      }
      try {
        final latest = await ref
            .read(appRepositoryProvider)
            .getSpeakingAttempt(current!.id);
        if (!mounted) {
          return;
        }
        ref.read(lastSpeakingAttemptProvider.notifier).state = latest;
        if (!_isAttemptProcessing(latest)) {
          _pollTimer?.cancel();
          _pollTimer = null;
          ref.invalidate(weeklyReportProvider);
        }
      } catch (error) {
        if (!_isPermanentAttemptFetchError(error)) {
          return;
        }
        if (!mounted) {
          return;
        }
        _pollTimer?.cancel();
        _pollTimer = null;
        setState(() {
          _pollingStoppedAttemptId = current?.id;
          _errorMessage = describeApiError(
            error,
            fallback: '录音结果暂时无法读取，请返回课程后重新进入。',
          );
        });
      }
    });
  }
}

class _RecordingActions extends StatelessWidget {
  const _RecordingActions({
    required this.recorder,
    required this.isBusy,
    required this.onStart,
    required this.onStop,
    required this.onClear,
    required this.onSubmit,
  });

  final bool isBusy;
  final VoidCallback onClear;
  final VoidCallback? onSubmit;
  final VoidCallback onStart;
  final VoidCallback onStop;
  final SpeakingRecorderState recorder;

  @override
  Widget build(BuildContext context) {
    final canUseCapturedAudio =
        !isBusy && !recorder.isRecording && recorder.audioPath.isNotEmpty;
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: <Widget>[
        if (recorder.isRecording)
          FilledButton.icon(
            onPressed: isBusy ? null : onStop,
            icon: const Icon(Icons.stop_rounded),
            label: const Text('停止录音'),
          )
        else
          FilledButton.icon(
            onPressed: isBusy ? null : onStart,
            icon: const Icon(Icons.mic_rounded),
            label: Text(recorder.audioPath.isEmpty ? '开始录音' : '重新录音'),
          ),
        FilledButton.icon(
          onPressed: canUseCapturedAudio ? onSubmit : null,
          icon: const Icon(Icons.cloud_upload_rounded),
          label: Text(isBusy ? '评分中' : '提交评分'),
        ),
        OutlinedButton.icon(
          onPressed: canUseCapturedAudio ? onClear : null,
          icon: const Icon(Icons.refresh_rounded),
          label: const Text('清除录音'),
        ),
      ],
    );
  }
}

class _AttemptResult extends StatelessWidget {
  const _AttemptResult({
    required this.attempt,
    required this.onRetry,
  });

  final SpeakingAttempt? attempt;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final current = attempt;
    if (current == null) {
      return const AppCard(
        child: Text('提交一次跟读后，这里会显示转写、评分、逐词反馈和下一步练习建议。'),
      );
    }
    if (_isAttemptProcessing(current)) {
      return const AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('评分中', style: AppTextStyles.sectionTitle),
            SizedBox(height: AppSpacing.sm),
            LinearProgressIndicator(),
            SizedBox(height: AppSpacing.sm),
            Text('AI 正在分析孩子的发音、流利度和完整度。'),
          ],
        ),
      );
    }
    if (current.status == SpeakingAttemptStatus.failed) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('口语评分失败', style: AppTextStyles.sectionTitle),
            const SizedBox(height: AppSpacing.sm),
            Text(current.failureReason.isNotEmpty
                ? current.failureReason
                : '请稍后重新评分。'),
            const SizedBox(height: AppSpacing.md),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('重新评分'),
            ),
          ],
        ),
      );
    }
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('${current.overallScore?.round() ?? 0}',
              style: AppTextStyles.pageTitle),
          const SizedBox(height: AppSpacing.xs),
          Text(_scoreLine(current)),
          const SizedBox(height: AppSpacing.md),
          Text('识别文本：${current.transcript}'),
          const SizedBox(height: AppSpacing.sm),
          Text(current.feedback),
          if (current.wordFeedback.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: current.wordFeedback
                  .map(
                    (item) => Chip(
                      label: Text('${item.word} ${item.score?.round() ?? 0}'),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (current.suggestions.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            for (final suggestion in current.suggestions)
              Text('建议：$suggestion'),
          ],
        ],
      ),
    );
  }
}

bool _isAttemptProcessing(SpeakingAttempt? attempt) {
  return attempt?.status == SpeakingAttemptStatus.recordingUploaded ||
      attempt?.status == SpeakingAttemptStatus.transcribing ||
      attempt?.status == SpeakingAttemptStatus.queued;
}

bool _isPermanentAttemptFetchError(Object error) {
  if (error is! DioException) {
    return false;
  }
  final statusCode = error.response?.statusCode;
  if (statusCode == null) {
    return false;
  }
  return statusCode >= 400 &&
      statusCode < 500 &&
      statusCode != 408 &&
      statusCode != 429;
}

String _targetText(CourseMaterial? material) {
  for (final asset in material?.learningAssets ?? const <LearningAsset>[]) {
    final text = asset.pronunciationText.trim().isNotEmpty
        ? asset.pronunciationText.trim()
        : asset.text.trim();
    if (text.isNotEmpty) {
      return text;
    }
  }
  return material?.title.trim().isNotEmpty == true ? material!.title : '跟读这句话。';
}

String _scoreLine(SpeakingAttempt attempt) {
  final pronunciation = ((attempt.pronunciationScore ?? 0) * 100).round();
  final accuracy = attempt.accuracyScore?.round() ?? 0;
  final fluency = attempt.fluencyScore?.round() ?? 0;
  final completeness = attempt.completenessScore?.round() ?? 0;
  return '发音 $pronunciation · 准确 $accuracy · 流利 $fluency · 完整 $completeness';
}
