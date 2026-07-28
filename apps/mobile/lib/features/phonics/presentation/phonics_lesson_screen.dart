import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/assets/app_illustrations.dart';
import '../../../core/audio/audio_player_controller.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/audio_play_button.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/no_child_state_panel.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';
import '../../speaking/data/speaking_recorder_controller.dart';
import '../data/phonics_providers.dart';
import 'widgets/phonics_letter_tile.dart';
import 'widgets/phonics_mic_button.dart';

/// The Blevins 4-step phonics lesson: 听音识音 → 圈首音 → 拼读 → 高频词, then a
/// completion stage. Steps are rendered in the order the backend returns them;
/// [_stepIndex] advances through `detail.steps` and, past the last step, shows
/// the completion summary.
class PhonicsLessonScreen extends ConsumerStatefulWidget {
  const PhonicsLessonScreen({
    required this.unitId,
    super.key,
  });

  final String unitId;

  @override
  ConsumerState<PhonicsLessonScreen> createState() =>
      _PhonicsLessonScreenState();
}

class _PhonicsLessonScreenState extends ConsumerState<PhonicsLessonScreen> {
  int _stepIndex = 0;

  @override
  void dispose() {
    // Stop any card/keyword playback when leaving the lesson.
    try {
      ref.read(audioPlaybackControllerProvider.notifier).stop();
    } catch (_) {}
    super.dispose();
  }

  void _advanceStep() {
    if (mounted) {
      setState(() => _stepIndex += 1);
    }
  }

  void _restart() {
    if (mounted) {
      setState(() => _stepIndex = 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final child = ref.watch(activeChildProvider);
    final detailAsync = ref.watch(phonicsUnitProvider(widget.unitId));

    return Scaffold(
      appBar: AppBar(title: const Text('自然拼读')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: child == null
            ? const NoChildStatePanel(description: '自然拼读需要先为孩子建立档案。')
            : detailAsync.when(
                data: (detail) => _buildBody(detail, child),
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (error, _) => _buildError(error),
              ),
      ),
    );
  }

  Widget _buildError(Object error) {
    if (isNotFoundApiError(error)) {
      return StatePanel(
        title: '这一课暂时找不到',
        description: '这节拼读课可能还没准备好，先回到拼读列表看看其它课程。',
        assetPath: AppIllustrations.stateEmpty,
        action: FilledButton(
          onPressed: () => context.go('/phonics'),
          child: const Text('返回拼读列表'),
        ),
      );
    }
    return StatePanel(
      title: '拼读课加载失败',
      description: describeApiError(error, fallback: '拼读课加载失败，请稍后重试。'),
      assetPath: AppIllustrations.stateError,
      action: FilledButton(
        onPressed: () => ref.invalidate(phonicsUnitProvider(widget.unitId)),
        child: const Text('重新加载'),
      ),
    );
  }

  Widget _buildBody(PhonicsUnitDetailResponse detail, ChildProfile child) {
    final steps = detail.steps;
    if (steps.isEmpty) {
      return StatePanel(
        title: '这一课还没有内容',
        description: '拼读内容正在准备中，稍后再来学习吧。',
        assetPath: AppIllustrations.stateEmpty,
        action: FilledButton(
          onPressed: () => context.go('/phonics'),
          child: const Text('返回拼读列表'),
        ),
      );
    }
    if (_stepIndex >= steps.length) {
      return _PhonicsCompletionStage(
        unitId: widget.unitId,
        unitTitle: detail.unit.title,
        fallbackProgress: detail.progress,
        onRestart: _restart,
      );
    }

    final step = steps[_stepIndex];
    final header = _LessonStepHeader(
      stepIndex: _stepIndex,
      totalSteps: steps.length,
      step: step,
    );

    if (step.practiceType == PhonicsPracticeType.firstSoundTap) {
      return _FirstSoundStage(
        header: header,
        unitId: widget.unitId,
        step: step,
        items: _resolveItems(detail, step),
        childId: child.id,
        onNext: _advanceStep,
      );
    }
    if (step.practiceType == PhonicsPracticeType.blendWordAsr) {
      return _BlendingStage(
        header: header,
        unitId: widget.unitId,
        step: step,
        words: _resolveWords(detail, step),
        cardsByLetter: _cardsByLetter(detail),
        childId: child.id,
        onNext: _advanceStep,
      );
    }
    if (step.practiceType == PhonicsPracticeType.tileBuild) {
      return _TileBuildStage(
        header: header,
        unitId: widget.unitId,
        step: step,
        words: _resolveWords(detail, step),
        childId: child.id,
        onNext: _advanceStep,
      );
    }
    if (step.practiceType == PhonicsPracticeType.dictation) {
      return _DictationStage(
        header: header,
        unitId: widget.unitId,
        step: step,
        words: _resolveWords(detail, step),
        unitLetters: detail.unit.letters,
        childId: child.id,
        onNext: _advanceStep,
      );
    }
    if (step.key == 'heart_word' ||
        (step.heartWords.isNotEmpty && step.cardIds.isEmpty)) {
      return _HeartWordStage(
        header: header,
        heartWords: _resolveHeartWords(detail, step),
        onNext: _advanceStep,
      );
    }
    // Default: 听音识音 (sound_intro) or any card-driven "none" step.
    return _SoundIntroStage(
      header: header,
      cards: _resolveCards(detail, step),
      onNext: _advanceStep,
    );
  }

  List<PhonicsSoundCard> _resolveCards(
      PhonicsUnitDetailResponse detail, PhonicsStep step) {
    final byId = <String, PhonicsSoundCard>{
      for (final card in detail.soundCards) card.id: card,
    };
    return <PhonicsSoundCard>[
      for (final id in step.cardIds)
        if (byId[id] != null) byId[id]!,
    ];
  }

  List<PhonicsFirstSoundItem> _resolveItems(
      PhonicsUnitDetailResponse detail, PhonicsStep step) {
    final byId = <String, PhonicsFirstSoundItem>{
      for (final item in detail.firstSoundItems) item.id: item,
    };
    return <PhonicsFirstSoundItem>[
      for (final id in step.itemIds)
        if (byId[id] != null) byId[id]!,
    ];
  }

  List<PhonicsDecodableWord> _resolveWords(
      PhonicsUnitDetailResponse detail, PhonicsStep step) {
    final byId = <String, PhonicsDecodableWord>{
      for (final word in detail.decodableWords) word.id: word,
    };
    return <PhonicsDecodableWord>[
      for (final id in step.wordIds)
        if (byId[id] != null) byId[id]!,
    ];
  }

  List<PhonicsHeartWord> _resolveHeartWords(
      PhonicsUnitDetailResponse detail, PhonicsStep step) {
    final byText = <String, PhonicsHeartWord>{
      for (final word in detail.heartWords) word.text: word,
    };
    return <PhonicsHeartWord>[
      for (final text in step.heartWords)
        if (byText[text] != null) byText[text]!,
    ];
  }

  Map<String, PhonicsSoundCard> _cardsByLetter(
      PhonicsUnitDetailResponse detail) {
    return <String, PhonicsSoundCard>{
      for (final card in detail.soundCards) card.letter: card,
    };
  }
}

// --- Shared step header ------------------------------------------------------

class _LessonStepHeader extends StatelessWidget {
  const _LessonStepHeader({
    required this.stepIndex,
    required this.totalSteps,
    required this.step,
  });

  final PhonicsStep step;
  final int stepIndex;
  final int totalSteps;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('第 ${stepIndex + 1} 步 / 共 $totalSteps 步',
              style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.xs),
          LinearProgressIndicator(
            value: (stepIndex + 1) / totalSteps,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppRadii.pill),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(step.title, style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.xs),
          Text(step.instruction, style: AppTextStyles.body),
        ],
      ),
    );
  }
}

// --- Step 1: 听音识音 --------------------------------------------------------

class _SoundIntroStage extends StatelessWidget {
  const _SoundIntroStage({
    required this.header,
    required this.cards,
    required this.onNext,
  });

  final List<PhonicsSoundCard> cards;
  final Widget header;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        header,
        const SizedBox(height: AppSpacing.md),
        for (final card in cards) ...<Widget>[
          _SoundCardView(card: card),
          const SizedBox(height: AppSpacing.md),
        ],
        Align(
          alignment: Alignment.bottomRight,
          child: FilledButton(
            onPressed: onNext,
            child: const Text('继续'),
          ),
        ),
      ],
    );
  }
}

class _SoundCardView extends StatelessWidget {
  const _SoundCardView({required this.card});

  final PhonicsSoundCard card;

  @override
  Widget build(BuildContext context) {
    final accent = card.isVowel ? AppColors.coralJam : AppColors.skyBlue;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 84,
                height: 84,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.24),
                  borderRadius: BorderRadius.circular(AppRadii.card),
                ),
                child: Text(card.letter, style: AppTextStyles.heroTitle),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(card.phoneme, style: AppTextStyles.pageTitle),
                    const SizedBox(height: AppSpacing.xxs),
                    Text('${card.keyword} · ${card.keywordCn}',
                        style: AppTextStyles.body),
                  ],
                ),
              ),
            ],
          ),
          if (card.articulationCue.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Text(card.articulationCue, style: AppTextStyles.body),
          ],
          if (card.exampleWords.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: <Widget>[
                for (final word in card.exampleWords)
                  Chip(label: Text('${word.text} ${word.cn}')),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              AudioPlayButton(
                url: card.soundAudioUrl,
                label: '听发音',
                unavailableLabel: '发音生成中',
              ),
              AudioPlayButton(
                url: card.keywordAudioUrl,
                label: '听例词',
                unavailableLabel: '例词生成中',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// --- Step 2: 圈首音 ----------------------------------------------------------

class _FirstSoundStage extends ConsumerStatefulWidget {
  const _FirstSoundStage({
    required this.header,
    required this.unitId,
    required this.step,
    required this.items,
    required this.childId,
    required this.onNext,
  });

  final String childId;
  final Widget header;
  final List<PhonicsFirstSoundItem> items;
  final VoidCallback onNext;
  final PhonicsStep step;
  final String unitId;

  @override
  ConsumerState<_FirstSoundStage> createState() => _FirstSoundStageState();
}

class _FirstSoundStageState extends ConsumerState<_FirstSoundStage> {
  int _itemIndex = 0;
  String? _selected;
  bool _wrongOnce = false;
  bool _locked = false;
  final List<PhonicsItemResult> _results = <PhonicsItemResult>[];
  bool _submitting = false;
  PhonicsAttemptResponse? _response;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        widget.header,
        const SizedBox(height: AppSpacing.md),
        if (_response != null) _resultCard(_response!) else _itemCard(),
      ],
    );
  }

  Widget _itemCard() {
    if (widget.items.isEmpty) {
      // Nothing to circle — don't strand the child; let them move on.
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('这一步暂时没有练习内容。'),
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: widget.onNext,
                child: const Text('继续'),
              ),
            ),
          ],
        ),
      );
    }

    final item = widget.items[_itemIndex];
    final feedback = _feedbackText(item);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('第 ${_itemIndex + 1}/${widget.items.length} 个词',
              style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          Text(item.text, style: AppTextStyles.heroTitle),
          const SizedBox(height: AppSpacing.xxs),
          Text(item.cn, style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.sm),
          AudioPlayButton(
            url: item.audioUrl,
            label: '播放单词',
            unavailableLabel: '单词发音生成中',
          ),
          const SizedBox(height: AppSpacing.md),
          Text('它的第一个音是哪个字母？', style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              for (final option in item.options)
                PhonicsLetterTile(
                  letter: option,
                  state: _tileState(item, option),
                  onTap: (_locked || _submitting)
                      ? null
                      : () => _onTapOption(item, option),
                ),
            ],
          ),
          if (feedback != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Text(feedback, style: AppTextStyles.body),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            Text(_error!, style: const TextStyle(color: AppColors.coralJam)),
          ],
          if (_locked) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: _submitting ? null : _advance,
                child: Text(
                  _submitting
                      ? '提交中'
                      : (_itemIndex + 1 == widget.items.length ? '看看结果' : '继续'),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _resultCard(PhonicsAttemptResponse response) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('圈首音完成', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          Text(response.attempt.feedback.isNotEmpty
              ? response.attempt.feedback
              : '完成啦，继续加油！'),
          const SizedBox(height: AppSpacing.xs),
          Text(
            '圈首音正确率 ${(response.progress.firstSoundAccuracy * 100).round()}%',
            style: AppTextStyles.helper,
          ),
          const SizedBox(height: AppSpacing.md),
          Align(
            alignment: Alignment.bottomRight,
            child: FilledButton(
              onPressed: widget.onNext,
              child: const Text('继续'),
            ),
          ),
        ],
      ),
    );
  }

  PhonicsTileState _tileState(PhonicsFirstSoundItem item, String option) {
    if (_selected != option) {
      return PhonicsTileState.idle;
    }
    return option == item.answer
        ? PhonicsTileState.correct
        : PhonicsTileState.incorrect;
  }

  String? _feedbackText(PhonicsFirstSoundItem item) {
    if (_locked) {
      final last = _results.isNotEmpty ? _results.last : null;
      if (last != null && last.correct) {
        return '答对啦！';
      }
      return '正确答案是 ${item.answer}。';
    }
    if (_wrongOnce) {
      return '再听一次，选出它的第一个音。';
    }
    return null;
  }

  void _onTapOption(PhonicsFirstSoundItem item, String option) {
    if (_locked || _submitting) {
      return;
    }
    final correct = option == item.answer;
    setState(() {
      _selected = option;
      if (correct) {
        _locked = true;
        _results.add(PhonicsItemResult(
          prompt: item.text,
          expected: item.answer,
          given: option,
          correct: true,
        ));
      } else if (_wrongOnce) {
        // Second miss — record the final answer and move on.
        _locked = true;
        _results.add(PhonicsItemResult(
          prompt: item.text,
          expected: item.answer,
          given: option,
          correct: false,
        ));
      } else {
        // First miss — let them try once more before it locks.
        _wrongOnce = true;
      }
    });
  }

  void _advance() {
    if (_itemIndex + 1 < widget.items.length) {
      setState(() {
        _itemIndex += 1;
        _selected = null;
        _wrongOnce = false;
        _locked = false;
        _error = null;
      });
    } else {
      _submit();
    }
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final response =
          await ref.read(appRepositoryProvider).submitPhonicsTapAttempt(
                childId: widget.childId,
                unitId: widget.unitId,
                step: widget.step.key,
                practiceType: widget.step.practiceType.value,
                itemResults: _results,
              );
      if (!mounted) {
        return;
      }
      setState(() => _response = response);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = describeApiError(error, fallback: '提交失败，请稍后重试。'));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

// --- Step 3: 拼读（录音 + ASR）----------------------------------------------

class _BlendingStage extends ConsumerStatefulWidget {
  const _BlendingStage({
    required this.header,
    required this.unitId,
    required this.step,
    required this.words,
    required this.cardsByLetter,
    required this.childId,
    required this.onNext,
  });

  final Map<String, PhonicsSoundCard> cardsByLetter;
  final String childId;
  final Widget header;
  final VoidCallback onNext;
  final PhonicsStep step;
  final String unitId;
  final List<PhonicsDecodableWord> words;

  @override
  ConsumerState<_BlendingStage> createState() => _BlendingStageState();
}

class _BlendingStageState extends ConsumerState<_BlendingStage> {
  int _wordIndex = 0;
  PhonicsAttempt? _attempt;
  bool _isSubmitting = false;
  String? _errorMessage;
  Timer? _pollTimer;
  int _pollTicks = 0;
  bool _pollTimedOut = false;
  String? _pollingStoppedAttemptId;

  @override
  void dispose() {
    _pollTimer?.cancel();
    try {
      ref.read(audioPlaybackControllerProvider.notifier).stop();
    } catch (_) {}
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.words.isEmpty) {
      return ListView(
        children: <Widget>[
          widget.header,
          const SizedBox(height: AppSpacing.md),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text('这一步暂时没有拼读的单词。'),
                const SizedBox(height: AppSpacing.md),
                Align(
                  alignment: Alignment.bottomRight,
                  child: FilledButton(
                    onPressed: widget.onNext,
                    child: const Text('继续'),
                  ),
                ),
              ],
            ),
          ),
        ],
      );
    }

    final word = widget.words[_wordIndex];
    final recorderAsync = ref.watch(speakingRecorderControllerProvider);
    final recorder = recorderAsync.valueOrNull ?? const SpeakingRecorderState();
    _syncPolling(_attempt);

    final isBusy = _isSubmitting ||
        recorderAsync.isLoading ||
        (_isProcessing(_attempt) && !_pollTimedOut);
    final canSubmit =
        !isBusy && !recorder.isRecording && recorder.audioPath.isNotEmpty;

    return ListView(
      children: <Widget>[
        widget.header,
        const SizedBox(height: AppSpacing.md),
        _wordCard(word, recorder),
        const SizedBox(height: AppSpacing.md),
        Center(
          child: PhonicsMicButton(
            isRecording: recorder.isRecording,
            enabled: !isBusy,
            onStart: _startRecording,
            onStop: _stopRecording,
          ),
        ),
        if (recorder.errorMessage.isNotEmpty) ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          Text(recorder.errorMessage,
              style: const TextStyle(color: AppColors.coralJam)),
        ],
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          alignment: WrapAlignment.center,
          children: <Widget>[
            FilledButton.icon(
              onPressed: canSubmit ? _submit : null,
              icon: const Icon(Icons.cloud_upload_rounded),
              label: Text(_isSubmitting ? '提交中' : '提交给 AI'),
            ),
            TextButton(
              onPressed: isBusy ? null : _advanceWord,
              child: Text(_isLastWord ? '跳过并完成' : '跳过这个词'),
            ),
          ],
        ),
        if (_errorMessage != null) ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          Text(_errorMessage!,
              style: const TextStyle(color: AppColors.coralJam)),
        ],
        if (_pollTimedOut) ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          Align(
            alignment: Alignment.center,
            child: OutlinedButton.icon(
              onPressed: _refetch,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('重新查询结果'),
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        _resultSection(_attempt),
      ],
    );
  }

  bool get _isLastWord => _wordIndex + 1 >= widget.words.length;

  Widget _wordCard(PhonicsDecodableWord word, SpeakingRecorderState recorder) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('第 ${_wordIndex + 1}/${widget.words.length} 个词',
              style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          Center(
            child: Column(
              children: <Widget>[
                Text(word.text, style: AppTextStyles.heroTitle),
                const SizedBox(height: AppSpacing.xxs),
                Text(word.cn, style: AppTextStyles.body),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text('依次点每个字母听发音，再连起来读：', style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.sm),
          Center(
            child: Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: <Widget>[
                for (final segment in word.segments)
                  PhonicsLetterTile(
                    letter: segment,
                    showSpeaker: true,
                    onTap: recorder.isRecording
                        ? null
                        : () => _playLetter(segment),
                  ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Center(
            child: AudioPlayButton(
              url: word.audioUrl,
              label: '合起来读',
              unavailableLabel: '发音生成中',
              enabled: !recorder.isRecording,
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultSection(PhonicsAttempt? attempt) {
    if (attempt == null) {
      return AppCard(
        child: Text('录好后点「提交给 AI」，AI 会听你把 ${widget.words[_wordIndex].text} 读得准不准。',
            style: AppTextStyles.body),
      );
    }
    if (_isProcessing(attempt)) {
      return const AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('AI 正在听你读…', style: AppTextStyles.cardTitle),
            SizedBox(height: AppSpacing.sm),
            LinearProgressIndicator(),
          ],
        ),
      );
    }
    if (attempt.status == PhonicsAttemptStatus.scored && attempt.passed) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                const Icon(Icons.emoji_events_rounded,
                    color: AppColors.forestMint),
                const SizedBox(width: AppSpacing.xs),
                Text('读得不错！', style: AppTextStyles.sectionTitle),
              ],
            ),
            if (attempt.transcript.isNotEmpty) ...<Widget>[
              const SizedBox(height: AppSpacing.sm),
              Text('AI 听到：${attempt.transcript}', style: AppTextStyles.body),
            ],
            if (attempt.feedback.isNotEmpty) ...<Widget>[
              const SizedBox(height: AppSpacing.xs),
              Text(attempt.feedback, style: AppTextStyles.body),
            ],
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: _advanceWord,
                child: Text(_isLastWord ? '完成拼读' : '继续下一个词'),
              ),
            ),
          ],
        ),
      );
    }
    if (attempt.status == PhonicsAttemptStatus.failed) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('这次没评上分', style: AppTextStyles.sectionTitle),
            const SizedBox(height: AppSpacing.sm),
            Text(attempt.failureReason.isNotEmpty
                ? attempt.failureReason
                : '再录一次试试，或先跳过这个词。'),
          ],
        ),
      );
    }
    // scored-but-not-passed or no_match — a normal "try again", not an error.
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('再试一次', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          Text(attempt.feedback.isNotEmpty
              ? attempt.feedback
              : '没太听清，深呼吸，把每个音慢慢连起来读一遍。'),
          const SizedBox(height: AppSpacing.sm),
          Text('点上面的麦克风就能重新录音。', style: AppTextStyles.helper),
        ],
      ),
    );
  }

  Future<void> _playLetter(String letter) async {
    final url = widget.cardsByLetter[letter]?.soundAudioUrl ?? '';
    if (url.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('这个字母的发音还在生成中')),
        );
      }
      return;
    }
    try {
      await ref.read(audioPlaybackControllerProvider.notifier).toggle(url);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('音频播放失败，请检查网络后重试。')),
        );
      }
    }
  }

  Future<void> _startRecording() async {
    try {
      await ref.read(audioPlaybackControllerProvider.notifier).stop();
      await ref.read(speakingRecorderControllerProvider.notifier).start();
      if (mounted) {
        setState(() => _errorMessage = null);
      }
    } catch (error) {
      if (mounted) {
        setState(() =>
            _errorMessage = describeApiError(error, fallback: '录音启动失败，请检查麦克风权限。'));
      }
    }
  }

  Future<void> _stopRecording() async {
    try {
      await ref.read(speakingRecorderControllerProvider.notifier).stop();
      if (mounted) {
        setState(() => _errorMessage = null);
      }
    } catch (error) {
      if (mounted) {
        setState(() =>
            _errorMessage = describeApiError(error, fallback: '录音保存失败，请重新录一次。'));
      }
    }
  }

  Future<void> _submit() async {
    final recorder = ref.read(speakingRecorderControllerProvider).valueOrNull;
    if (recorder == null || recorder.audioPath.isEmpty) {
      setState(() => _errorMessage = '请先录一段拼读音频。');
      return;
    }
    if (recorder.isRecording) {
      setState(() => _errorMessage = '请先停止录音，再提交。');
      return;
    }
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
      _pollingStoppedAttemptId = null;
      _pollTimedOut = false;
    });
    try {
      final created =
          await ref.read(appRepositoryProvider).uploadPhonicsWordAttempt(
                childId: widget.childId,
                unitId: widget.unitId,
                targetText: widget.words[_wordIndex].text,
                filePath: recorder.audioPath,
                durationMs: recorder.durationMs,
              );
      if (!mounted) {
        return;
      }
      setState(() => _attempt = created);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() =>
          _errorMessage = describeApiError(error, fallback: '提交失败，请稍后重试。'));
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _advanceWord() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _pollTicks = 0;
    _pollTimedOut = false;
    _pollingStoppedAttemptId = null;
    // Reset the shared recorder for the next word.
    ref.read(speakingRecorderControllerProvider.notifier).clear();
    if (_isLastWord) {
      widget.onNext();
      return;
    }
    setState(() {
      _wordIndex += 1;
      _attempt = null;
      _errorMessage = null;
    });
  }

  Future<void> _refetch() async {
    final current = _attempt;
    if (current == null) {
      return;
    }
    setState(() {
      _pollTimedOut = false;
      _pollingStoppedAttemptId = null;
      _errorMessage = null;
    });
    try {
      final latest =
          await ref.read(appRepositoryProvider).getPhonicsAttempt(current.id);
      if (!mounted) {
        return;
      }
      setState(() => _attempt = latest);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() =>
          _errorMessage = describeApiError(error, fallback: '查询结果失败，请稍后再试。'));
    }
  }

  void _syncPolling(PhonicsAttempt? attempt) {
    if (!_isProcessing(attempt)) {
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
    if (_pollTimer != null) {
      return;
    }
    _pollTicks = 0;
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      final current = _attempt;
      if (!_isProcessing(current)) {
        _pollTimer?.cancel();
        _pollTimer = null;
        return;
      }
      _pollTicks += 1;
      if (_pollTicks > 60) {
        // ~180s wall-clock: cover the worker's hard time limit so a late score
        // still lands, then stop the spinner and let the child re-query/re-record.
        _pollTimer?.cancel();
        _pollTimer = null;
        if (mounted) {
          setState(() {
            _pollingStoppedAttemptId = current?.id;
            _pollTimedOut = true;
            _errorMessage = '评分用时较长，可稍后重新查询，或重新录一次。';
          });
        }
        return;
      }
      try {
        final latest =
            await ref.read(appRepositoryProvider).getPhonicsAttempt(current!.id);
        if (!mounted) {
          return;
        }
        setState(() => _attempt = latest);
        if (!_isProcessing(latest)) {
          _pollTimer?.cancel();
          _pollTimer = null;
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
            fallback: '录音结果暂时无法读取，请稍后重试。',
          );
        });
      }
    });
  }
}

// --- Extra step: 搭词 (tile build — the word IS shown) ----------------------

class _TileBuildStage extends ConsumerStatefulWidget {
  const _TileBuildStage({
    required this.header,
    required this.unitId,
    required this.step,
    required this.words,
    required this.childId,
    required this.onNext,
  });

  final String childId;
  final Widget header;
  final VoidCallback onNext;
  final PhonicsStep step;
  final String unitId;
  final List<PhonicsDecodableWord> words;

  @override
  ConsumerState<_TileBuildStage> createState() => _TileBuildStageState();
}

class _TileBuildStageState extends ConsumerState<_TileBuildStage> {
  int _wordIndex = 0;
  // The ordered answer row; nulls are empty slots. Kept in sync with [_bank]:
  // placing a tile moves it out of the bank, clearing a slot returns it.
  late List<String?> _slots;
  late List<String> _bank;
  bool _locked = false;
  final List<PhonicsItemResult> _results = <PhonicsItemResult>[];
  bool _submitting = false;
  PhonicsAttemptResponse? _response;
  String? _error;

  @override
  void initState() {
    super.initState();
    _setupWord();
  }

  /// Reset slots/bank for the current word. The bank is shuffled once here (not
  /// in build) so it stays stable across rebuilds; each segment tile is its own
  /// bank entry, so duplicate letters (d, a, d) each stay individually tappable.
  void _setupWord() {
    if (widget.words.isEmpty) {
      _slots = <String?>[];
      _bank = <String>[];
      return;
    }
    final word = widget.words[_wordIndex];
    _slots = List<String?>.filled(word.segments.length, null);
    _bank = List<String>.of(word.segments)..shuffle();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        widget.header,
        const SizedBox(height: AppSpacing.md),
        if (_response != null) _resultCard(_response!) else _wordCard(),
      ],
    );
  }

  Widget _wordCard() {
    if (widget.words.isEmpty) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('这一步暂时没有可以搭的单词。'),
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: widget.onNext,
                child: const Text('继续'),
              ),
            ),
          ],
        ),
      );
    }

    final word = widget.words[_wordIndex];
    final expected = word.segments.join('');
    final assembled = _slots.map((slot) => slot ?? '').join('');
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('第 ${_wordIndex + 1}/${widget.words.length} 个词',
              style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          Center(
            child: Column(
              children: <Widget>[
                Text(word.text, style: AppTextStyles.heroTitle),
                const SizedBox(height: AppSpacing.xxs),
                Text(word.cn, style: AppTextStyles.body),
                const SizedBox(height: AppSpacing.sm),
                AudioPlayButton(
                  url: word.audioUrl,
                  label: '听单词',
                  unavailableLabel: '发音生成中',
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text('把下面的字母排成正确的顺序：', style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.sm),
          _answerRow(word),
          const SizedBox(height: AppSpacing.md),
          Text('字母卡片', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          _tileBank(),
          if (_locked) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Text(
              assembled == expected ? '搭对啦！' : '正确的拼法是 $expected。',
              style: AppTextStyles.body,
            ),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            Text(_error!, style: const TextStyle(color: AppColors.coralJam)),
          ],
          if (_locked) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: _submitting ? null : _advance,
                child: Text(
                  _submitting
                      ? '提交中'
                      : (_wordIndex + 1 == widget.words.length ? '看看结果' : '继续'),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _answerRow(PhonicsDecodableWord word) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: <Widget>[
        for (var i = 0; i < _slots.length; i++)
          _slots[i] == null
              ? _emptySlot()
              : PhonicsLetterTile(
                  letter: _slots[i]!,
                  state: _slotState(word, i),
                  onTap: (_locked || _submitting) ? null : () => _clearSlot(i),
                ),
      ],
    );
  }

  Widget _tileBank() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: <Widget>[
        for (var i = 0; i < _bank.length; i++)
          PhonicsLetterTile(
            letter: _bank[i],
            onTap: (_locked || _submitting) ? null : () => _placeTile(i),
          ),
      ],
    );
  }

  PhonicsTileState _slotState(PhonicsDecodableWord word, int index) {
    if (!_locked) {
      return PhonicsTileState.idle;
    }
    final expected = index < word.segments.length ? word.segments[index] : '';
    return _slots[index] == expected
        ? PhonicsTileState.correct
        : PhonicsTileState.incorrect;
  }

  void _placeTile(int bankIndex) {
    if (_locked || _submitting) {
      return;
    }
    final slotIndex = _slots.indexOf(null);
    if (slotIndex == -1) {
      return;
    }
    setState(() {
      _slots[slotIndex] = _bank.removeAt(bankIndex);
      if (!_slots.contains(null)) {
        _lockAndRecord();
      }
    });
  }

  void _clearSlot(int slotIndex) {
    if (_locked || _submitting) {
      return;
    }
    final letter = _slots[slotIndex];
    if (letter == null) {
      return;
    }
    setState(() {
      _slots[slotIndex] = null;
      _bank.add(letter);
    });
  }

  void _lockAndRecord() {
    final word = widget.words[_wordIndex];
    final expected = word.segments.join('');
    final assembled = _slots.map((slot) => slot ?? '').join('');
    _locked = true;
    _results.add(PhonicsItemResult(
      prompt: word.text,
      expected: expected,
      given: assembled,
      correct: assembled == expected,
    ));
  }

  void _advance() {
    if (_wordIndex + 1 < widget.words.length) {
      setState(() {
        _wordIndex += 1;
        _locked = false;
        _error = null;
        _setupWord();
      });
    } else {
      _submit();
    }
  }

  Widget _resultCard(PhonicsAttemptResponse response) {
    final correctCount = _results.where((result) => result.correct).length;
    final total = _results.length;
    final accuracy = total == 0 ? 0 : (correctCount / total * 100).round();
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('搭词完成', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          Text('搭对 $correctCount/$total 个。'),
          const SizedBox(height: AppSpacing.xs),
          Text('正确率 $accuracy%', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.md),
          Align(
            alignment: Alignment.bottomRight,
            child: FilledButton(
              onPressed: widget.onNext,
              child: const Text('继续'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final response =
          await ref.read(appRepositoryProvider).submitPhonicsTapAttempt(
                childId: widget.childId,
                unitId: widget.unitId,
                step: widget.step.key,
                practiceType: widget.step.practiceType.value,
                itemResults: _results,
              );
      if (!mounted) {
        return;
      }
      setState(() => _response = response);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = describeApiError(error, fallback: '提交失败，请稍后重试。'));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

// --- Extra step: 听写 (dictation — the word is NOT shown) --------------------

class _DictationStage extends ConsumerStatefulWidget {
  const _DictationStage({
    required this.header,
    required this.unitId,
    required this.step,
    required this.words,
    required this.unitLetters,
    required this.childId,
    required this.onNext,
  });

  final String childId;
  final Widget header;
  final VoidCallback onNext;
  final PhonicsStep step;
  final String unitId;
  final List<String> unitLetters;
  final List<PhonicsDecodableWord> words;

  @override
  ConsumerState<_DictationStage> createState() => _DictationStageState();
}

class _DictationStageState extends ConsumerState<_DictationStage> {
  int _wordIndex = 0;
  // Same slot/bank model as _TileBuildStage; here the bank also carries up to 2
  // distractor letters, so the child can place a wrong tile and lock incorrect.
  late List<String?> _slots;
  late List<String> _bank;
  bool _locked = false;
  final List<PhonicsItemResult> _results = <PhonicsItemResult>[];
  bool _submitting = false;
  PhonicsAttemptResponse? _response;
  String? _error;

  @override
  void initState() {
    super.initState();
    _setupWord();
  }

  /// Reset slots for the current word and build a shuffled bank of its segments
  /// plus up to 2 distractor tiles drawn from the unit's other letters. Shuffled
  /// once here (not in build) so the order is stable across rebuilds.
  void _setupWord() {
    if (widget.words.isEmpty) {
      _slots = <String?>[];
      _bank = <String>[];
      return;
    }
    final word = widget.words[_wordIndex];
    _slots = List<String?>.filled(word.segments.length, null);
    final segments = word.segments.toSet();
    final distractors = widget.unitLetters
        .where((letter) => letter.isNotEmpty && !segments.contains(letter))
        .toSet()
        .toList()
      ..shuffle();
    _bank = <String>[...word.segments, ...distractors.take(2)]..shuffle();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        widget.header,
        const SizedBox(height: AppSpacing.md),
        if (_response != null) _resultCard(_response!) else _wordCard(),
      ],
    );
  }

  Widget _wordCard() {
    if (widget.words.isEmpty) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('这一步暂时没有可以听写的单词。'),
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: widget.onNext,
                child: const Text('继续'),
              ),
            ),
          ],
        ),
      );
    }

    final word = widget.words[_wordIndex];
    final expected = word.segments.join('');
    final assembled = _slots.map((slot) => slot ?? '').join('');
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('第 ${_wordIndex + 1}/${widget.words.length} 个词',
              style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          Center(
            child: Column(
              children: <Widget>[
                Text('先听一听，再把字母拼出来', style: AppTextStyles.sectionTitle),
                const SizedBox(height: AppSpacing.xxs),
                Text('小提示：${word.cn}', style: AppTextStyles.body),
                const SizedBox(height: AppSpacing.sm),
                AudioPlayButton(
                  url: word.audioUrl,
                  label: '再听一次',
                  unavailableLabel: '发音生成中',
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text('按听到的顺序把字母排好：', style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.sm),
          _answerRow(word),
          const SizedBox(height: AppSpacing.md),
          Text('字母卡片', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.sm),
          _tileBank(),
          if (_locked) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Text(
              assembled == expected ? '拼对啦！' : '正确的拼法是 $expected。',
              style: AppTextStyles.body,
            ),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            Text(_error!, style: const TextStyle(color: AppColors.coralJam)),
          ],
          if (_locked) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.bottomRight,
              child: FilledButton(
                onPressed: _submitting ? null : _advance,
                child: Text(
                  _submitting
                      ? '提交中'
                      : (_wordIndex + 1 == widget.words.length ? '看看结果' : '继续'),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _answerRow(PhonicsDecodableWord word) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: <Widget>[
        for (var i = 0; i < _slots.length; i++)
          _slots[i] == null
              ? _emptySlot()
              : PhonicsLetterTile(
                  letter: _slots[i]!,
                  state: _slotState(word, i),
                  onTap: (_locked || _submitting) ? null : () => _clearSlot(i),
                ),
      ],
    );
  }

  Widget _tileBank() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: <Widget>[
        for (var i = 0; i < _bank.length; i++)
          PhonicsLetterTile(
            letter: _bank[i],
            onTap: (_locked || _submitting) ? null : () => _placeTile(i),
          ),
      ],
    );
  }

  PhonicsTileState _slotState(PhonicsDecodableWord word, int index) {
    if (!_locked) {
      return PhonicsTileState.idle;
    }
    final expected = index < word.segments.length ? word.segments[index] : '';
    return _slots[index] == expected
        ? PhonicsTileState.correct
        : PhonicsTileState.incorrect;
  }

  void _placeTile(int bankIndex) {
    if (_locked || _submitting) {
      return;
    }
    final slotIndex = _slots.indexOf(null);
    if (slotIndex == -1) {
      return;
    }
    setState(() {
      _slots[slotIndex] = _bank.removeAt(bankIndex);
      if (!_slots.contains(null)) {
        _lockAndRecord();
      }
    });
  }

  void _clearSlot(int slotIndex) {
    if (_locked || _submitting) {
      return;
    }
    final letter = _slots[slotIndex];
    if (letter == null) {
      return;
    }
    setState(() {
      _slots[slotIndex] = null;
      _bank.add(letter);
    });
  }

  void _lockAndRecord() {
    final word = widget.words[_wordIndex];
    final expected = word.segments.join('');
    final assembled = _slots.map((slot) => slot ?? '').join('');
    _locked = true;
    _results.add(PhonicsItemResult(
      prompt: word.text,
      expected: expected,
      given: assembled,
      correct: assembled == expected,
    ));
  }

  void _advance() {
    if (_wordIndex + 1 < widget.words.length) {
      setState(() {
        _wordIndex += 1;
        _locked = false;
        _error = null;
        _setupWord();
      });
    } else {
      _submit();
    }
  }

  Widget _resultCard(PhonicsAttemptResponse response) {
    final correctCount = _results.where((result) => result.correct).length;
    final total = _results.length;
    final accuracy = total == 0 ? 0 : (correctCount / total * 100).round();
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('听写完成', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          Text('拼对 $correctCount/$total 个。'),
          const SizedBox(height: AppSpacing.xs),
          Text('正确率 $accuracy%', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.md),
          Align(
            alignment: Alignment.bottomRight,
            child: FilledButton(
              onPressed: widget.onNext,
              child: const Text('继续'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final response =
          await ref.read(appRepositoryProvider).submitPhonicsTapAttempt(
                childId: widget.childId,
                unitId: widget.unitId,
                step: widget.step.key,
                practiceType: widget.step.practiceType.value,
                itemResults: _results,
              );
      if (!mounted) {
        return;
      }
      setState(() => _response = response);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _error = describeApiError(error, fallback: '提交失败，请稍后重试。'));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}

/// A dashed/outlined empty answer slot, sized to match [PhonicsLetterTile].
Widget _emptySlot() {
  return Container(
    width: 76,
    height: 76,
    decoration: BoxDecoration(
      color: AppColors.paperWhite,
      borderRadius: BorderRadius.circular(AppRadii.card),
      border: Border.all(color: AppColors.outlineVariant, width: 2),
    ),
    child: const Icon(Icons.add_rounded, color: AppColors.outlineVariant),
  );
}

// --- Step 4: 高频词 ----------------------------------------------------------

class _HeartWordStage extends StatelessWidget {
  const _HeartWordStage({
    required this.header,
    required this.heartWords,
    required this.onNext,
  });

  final Widget header;
  final List<PhonicsHeartWord> heartWords;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        header,
        const SizedBox(height: AppSpacing.md),
        for (final word in heartWords) ...<Widget>[
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(word.text, style: AppTextStyles.heroTitle),
                const SizedBox(height: AppSpacing.xxs),
                Text(word.cn, style: AppTextStyles.body),
                const SizedBox(height: AppSpacing.sm),
                AudioPlayButton(
                  url: word.audioUrl,
                  label: '跟我读',
                  unavailableLabel: '发音生成中',
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        Align(
          alignment: Alignment.bottomRight,
          child: FilledButton(
            onPressed: onNext,
            child: const Text('完成这一课'),
          ),
        ),
      ],
    );
  }
}

// --- Completion --------------------------------------------------------------

class _PhonicsCompletionStage extends ConsumerWidget {
  const _PhonicsCompletionStage({
    required this.unitId,
    required this.unitTitle,
    required this.fallbackProgress,
    required this.onRestart,
  });

  final PhonicsProgress fallbackProgress;
  final VoidCallback onRestart;
  final String unitId;
  final String unitTitle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressAsync = ref.watch(phonicsProgressProvider);
    final response = progressAsync.valueOrNull;
    final progress = _progressFor(response) ?? fallbackProgress;
    final nextUnitId = response?.nextUnitId ?? '';
    final hasNext = nextUnitId.isNotEmpty && nextUnitId != unitId;

    return ListView(
      children: <Widget>[
        IllustratedHeroCard(
          eyebrow: '完成啦',
          title: progress.mastered ? '太棒了，这一课掌握啦！' : '这一课先到这里，进步看得见！',
          description: '刚刚练完《$unitTitle》。多读几遍，拼读会越来越顺。',
          accent: AppColors.mintLeaf,
          illustration: Icons.workspace_premium_rounded,
          assetPath: AppIllustrations.stateSuccess,
          badge: const StickerBadge(
            label: 'Good job',
            icon: Icons.celebration_rounded,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('学习成果', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              _statRow('拼读正确率',
                  '${(progress.decodingAccuracy * 100).round()}%'),
              _statRow('圈首音正确率',
                  '${(progress.firstSoundAccuracy * 100).round()}%'),
              _statRow('练习次数', '${progress.attemptsCount} 次'),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: <Widget>[
                  Icon(
                    progress.mastered
                        ? Icons.verified_rounded
                        : Icons.trending_up_rounded,
                    color: progress.mastered
                        ? AppColors.forestMint
                        : AppColors.coralJam,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Text(progress.mastered ? '本单元已掌握' : '继续练习就能掌握',
                      style: AppTextStyles.body),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: <Widget>[
            FilledButton.icon(
              onPressed: onRestart,
              icon: const Icon(Icons.replay_rounded),
              label: const Text('再练一次'),
            ),
            OutlinedButton(
              onPressed: () => context.go('/phonics'),
              child: const Text('返回拼读列表'),
            ),
            if (hasNext)
              OutlinedButton.icon(
                onPressed: () => context.go('/phonics/unit/$nextUnitId'),
                icon: const Icon(Icons.arrow_forward_rounded),
                label: const Text('下一课'),
              ),
          ],
        ),
      ],
    );
  }

  PhonicsProgress? _progressFor(PhonicsProgressResponse? response) {
    if (response == null) {
      return null;
    }
    for (final unit in response.units) {
      if (unit.unitId == unitId) {
        return unit;
      }
    }
    return null;
  }
}

Widget _statRow(String label, String value) {
  return Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.xs),
    child: Row(
      children: <Widget>[
        Expanded(child: Text(label, style: AppTextStyles.body)),
        Text(value, style: AppTextStyles.cardTitle),
      ],
    ),
  );
}

bool _isProcessing(PhonicsAttempt? attempt) {
  return attempt?.status == PhonicsAttemptStatus.queued ||
      attempt?.status == PhonicsAttemptStatus.recordingUploaded ||
      attempt?.status == PhonicsAttemptStatus.transcribing;
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
