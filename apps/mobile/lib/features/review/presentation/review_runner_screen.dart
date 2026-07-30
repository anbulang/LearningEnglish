import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/analytics/app_analytics.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/audio_play_button.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/no_child_state_panel.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';

class ReviewRunnerScreen extends ConsumerStatefulWidget {
  const ReviewRunnerScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  ConsumerState<ReviewRunnerScreen> createState() => _ReviewRunnerScreenState();
}

class _ReviewRunnerScreenState extends ConsumerState<ReviewRunnerScreen> {
  int _currentIndex = 0;
  bool _sessionRecorded = false;
  bool _submitting = false;
  final Map<String, PracticeTaskResult> _results = <String, PracticeTaskResult>{};
  PracticeSession? _finishedSession;

  @override
  Widget build(BuildContext context) {
    final allTasks = ref.watch(reviewTasksProvider);
    final child = ref.watch(activeChildProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('复习进行中')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: allTasks.when(
          data: (items) {
            final tasks = items
                .where((task) => task.materialId == widget.materialId)
                .toList();
            if (child == null) {
              return const NoChildStatePanel(description: '复习需要先为孩子建立档案。');
            }
            if (tasks.isEmpty) {
              return StatePanel(
                title: '这门课暂时没有复习任务',
                description: '复习任务可能还在生成，可以先回到课程，或换个方式练习。',
                assetPath: AppIllustrations.stateEmpty,
                action: Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  alignment: WrapAlignment.center,
                  children: <Widget>[
                    FilledButton(
                      onPressed: () =>
                          context.go('/lessons/${widget.materialId}'),
                      child: const Text('回到本课'),
                    ),
                    OutlinedButton(
                      onPressed: () =>
                          context.go('/review/speaking/${widget.materialId}'),
                      child: const Text('口语陪练'),
                    ),
                  ],
                ),
              );
            }
            final isFinished = _currentIndex >= tasks.length;
            if (isFinished) {
              return _ReviewFinishedState(
                materialId: widget.materialId,
                session: _finishedSession,
              );
            }
            final task = tasks[_currentIndex];
            return _ReviewTaskStage(
              task: task,
              currentIndex: _currentIndex,
              totalCount: tasks.length,
              result: _results[task.id],
              submitting: _submitting,
              onAnswer: (result) =>
                  setState(() => _results[result.taskId] = result),
              onNext: () => _handleNext(context, tasks, child.id),
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => StatePanel(
            title: '复习任务加载失败',
            description: describeApiError(error, fallback: '复习任务加载失败，请稍后重试。'),
            assetPath: AppIllustrations.stateError,
            action: FilledButton(
              onPressed: () => ref.invalidate(reviewTasksProvider),
              child: const Text('重新加载'),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleNext(
    BuildContext context,
    List<ReviewTask> tasks,
    String childId,
  ) async {
    final isLast = _currentIndex + 1 == tasks.length;
    if (!isLast) {
      setState(() => _currentIndex += 1);
      return;
    }
    if (_sessionRecorded || _submitting) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _submitting = true);
    try {
      final session =
          await ref.read(appRepositoryProvider).createPracticeSession(
                childId: childId,
                reviewTaskIds: tasks.map((task) => task.id).toList(),
                taskResults: tasks
                    .map((task) =>
                        _results[task.id] ??
                        PracticeTaskResult(taskId: task.id))
                    .toList(),
              );
      ref.invalidate(reviewTasksProvider);
      ref.invalidate(weeklyReportProvider);
      ref.read(appAnalyticsProvider).track('review_session_completed', {
        'materialId': widget.materialId,
        'taskCount': tasks.length,
      });
      if (!mounted) {
        return;
      }
      setState(() {
        _sessionRecorded = true;
        _finishedSession = session;
        _submitting = false;
        _currentIndex += 1;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _submitting = false);
      messenger.showSnackBar(
        SnackBar(
          content: Text(describeApiError(error, fallback: '提交复习结果失败，请稍后重试。')),
        ),
      );
    }
  }
}

class _ReviewTaskStage extends StatelessWidget {
  const _ReviewTaskStage({
    required this.task,
    required this.currentIndex,
    required this.totalCount,
    required this.result,
    required this.submitting,
    required this.onAnswer,
    required this.onNext,
  });

  final ReviewTask task;
  final int currentIndex;
  final int totalCount;
  final PracticeTaskResult? result;
  final bool submitting;
  final ValueChanged<PracticeTaskResult> onAnswer;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final isLast = currentIndex + 1 == totalCount;
    final answered = result != null;
    // Keep the action button pinned to the bottom when the task fits, but let a
    // tall task (large flashcard image + text) scroll instead of overflowing.
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: IntrinsicHeight(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  IllustratedHeroCard(
                    eyebrow: '复习进行中',
                    title: task.contentJson['prompt'] as String? ?? '复习任务',
                    description:
                        '第 ${currentIndex + 1} 题，共 $totalCount 题。一步一步完成就好。',
                    accent: _taskAccent(task.taskType),
                    illustration: _taskIcon(task.taskType),
                    assetPath: _taskAsset(task),
                    badge: StickerBadge(
                      label: '任务 ${currentIndex + 1}/$totalCount',
                      icon: Icons.flag_rounded,
                      color: _taskAccent(task.taskType).withValues(alpha: 0.55),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('任务 ${currentIndex + 1} / $totalCount',
                            style: AppTextStyles.helper),
                        const SizedBox(height: AppSpacing.xs),
                        LinearProgressIndicator(
                          value: (currentIndex + 1) / totalCount,
                          minHeight: 8,
                          borderRadius: BorderRadius.circular(AppRadii.pill),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        _TaskSurface(
                          // Reset per-task interaction state when the task changes.
                          key: ValueKey<String>(task.id),
                          task: task,
                          result: result,
                          onAnswer: onAnswer,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  const Spacer(),
                  Align(
                    alignment: Alignment.bottomRight,
                    child: FilledButton(
                      onPressed: (answered && !submitting) ? onNext : null,
                      child: submitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(isLast ? '完成本次复习' : '继续下一题'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _TaskSurface extends StatefulWidget {
  const _TaskSurface({
    required this.task,
    required this.result,
    required this.onAnswer,
    super.key,
  });

  final ReviewTask task;
  final PracticeTaskResult? result;
  final ValueChanged<PracticeTaskResult> onAnswer;

  @override
  State<_TaskSurface> createState() => _TaskSurfaceState();
}

class _TaskSurfaceState extends State<_TaskSurface> {
  String? _flashChoice;
  String? _listenPick;
  List<String> _shuffledRight = const <String>[];
  List<String?> _matchSelections = const <String?>[];

  @override
  void initState() {
    super.initState();
    final task = widget.task;
    if (task.taskType == TaskType.matchChoice) {
      final left = List<String>.from(
          task.contentJson['left'] as List<dynamic>? ?? const <String>[]);
      final right = List<String>.from(
          task.contentJson['right'] as List<dynamic>? ?? const <String>[]);
      _shuffledRight = <String>[...right]..shuffle();
      _matchSelections = List<String?>.filled(left.length, null);
    }
    // Passive task types carry no answer to capture — auto-record an empty
    // result so the "继续" button doesn't dead-end.
    if (task.taskType == TaskType.speakingPrompt ||
        task.taskType == TaskType.parentCoaching) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          widget.onAnswer(PracticeTaskResult(taskId: task.id));
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    switch (widget.task.taskType) {
      case TaskType.flashcard:
        return _buildFlashcard();
      case TaskType.listenChoice:
        return _buildListenChoice();
      case TaskType.matchChoice:
        return _buildMatchChoice();
      case TaskType.speakingPrompt:
      case TaskType.parentCoaching:
        return AppCard(
            child: Text(widget.task.contentJson['prompt'] as String? ?? '任务'));
    }
  }

  Widget _buildFlashcard() {
    final task = widget.task;
    final word = task.contentJson['word'] as String? ?? '';
    final assetPath =
        AppIllustrations.vocabularyFor(word) ?? AppIllustrations.heroLesson;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(40),
            child: Image.asset(
              assetPath,
              width: 148,
              height: 148,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                width: 148,
                height: 148,
                decoration: BoxDecoration(
                  color: AppColors.skyBlue.withValues(alpha: 0.25),
                  borderRadius: BorderRadius.circular(40),
                ),
                child: const Icon(Icons.pets_rounded,
                    size: 64, color: AppColors.cocoaCoral),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(word, style: AppTextStyles.pageTitle),
          const SizedBox(height: AppSpacing.sm),
          Text(task.contentJson['hint'] as String? ?? '点击播放音频并跟读'),
          const SizedBox(height: AppSpacing.md),
          // Only offer playback when there is a real audio URL. Stub-generated
          // flashcards carry none, so an empty AudioPlayButton would sit on a
          // misleading permanent「发音生成中」instead of a clear "no audio" note.
          if ((task.contentJson['audio_url'] as String? ?? '').isNotEmpty)
            AudioPlayButton(
              url: task.contentJson['audio_url'] as String,
              label: '播放发音',
            )
          else
            Text('该词暂无标准音', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.lg),
          Row(
            children: <Widget>[
              Expanded(
                child: _SelectableButton(
                  label: '我会读',
                  icon: Icons.sentiment_very_satisfied_rounded,
                  color: AppColors.mintLeaf,
                  selected: _flashChoice == 'known',
                  onPressed: () => _pickFlashcard('known'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: _SelectableButton(
                  label: '还不熟',
                  icon: Icons.self_improvement_rounded,
                  color: AppColors.butterYellow,
                  selected: _flashChoice == 'unknown',
                  onPressed: () => _pickFlashcard('unknown'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _pickFlashcard(String answer) {
    setState(() => _flashChoice = answer);
    widget.onAnswer(
        PracticeTaskResult(taskId: widget.task.id, answer: answer));
  }

  Widget _buildListenChoice() {
    final task = widget.task;
    final choices = List<String>.from(
        task.contentJson['choices'] as List<dynamic>? ?? const <String>[]);
    final correct = task.contentJson['correct_answer'] as String? ?? '';
    final audioUrl = task.contentJson['audio_url'] as String? ?? '';
    final picked = _listenPick;
    return Column(
      children: <Widget>[
        if (audioUrl.isNotEmpty) ...<Widget>[
          AudioPlayButton(url: audioUrl, label: '播放发音'),
          const SizedBox(height: AppSpacing.md),
        ],
        ...choices.map((choice) {
          final isPicked = picked == choice;
          final isCorrect = choice == correct;
          Color? background;
          Widget? trailing;
          if (picked != null) {
            if (isCorrect) {
              background = AppColors.mintLeaf.withValues(alpha: 0.22);
              trailing = const Icon(Icons.check_circle_rounded,
                  color: AppColors.mintLeaf);
            } else if (isPicked) {
              background = AppColors.coralJam.withValues(alpha: 0.18);
              trailing =
                  const Icon(Icons.cancel_rounded, color: AppColors.coralJam);
            }
          }
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: background ?? AppColors.paperWhite,
                borderRadius: BorderRadius.circular(AppRadii.card),
                boxShadow: AppShadows.card,
              ),
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                onTap: picked == null ? () => _pickListen(choice) : null,
                leading: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: AppColors.skyBlue.withValues(alpha: 0.22),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: Image.asset(
                    AppIllustrations.vocabularyFor(choice) ??
                        AppIllustrations.heroLesson,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const Icon(
                        Icons.hearing_rounded,
                        color: AppColors.cocoaCoral),
                  ),
                ),
                title: Text(choice),
                trailing: trailing,
              ),
            ),
          );
        }),
      ],
    );
  }

  void _pickListen(String choice) {
    setState(() => _listenPick = choice);
    widget.onAnswer(
        PracticeTaskResult(taskId: widget.task.id, answer: choice));
  }

  Widget _buildMatchChoice() {
    final task = widget.task;
    final left = List<String>.from(
        task.contentJson['left'] as List<dynamic>? ?? const <String>[]);
    final right = List<String>.from(
        task.contentJson['right'] as List<dynamic>? ?? const <String>[]);
    final allAssigned =
        _matchSelections.isNotEmpty && _matchSelections.every((e) => e != null);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('点击右侧按钮，为每个词选出对应的答案。', style: AppTextStyles.helper),
          const SizedBox(height: AppSpacing.md),
          ...List<Widget>.generate(left.length, (index) {
            final selection = _matchSelections[index];
            final isCorrect =
                allAssigned && index < right.length && selection == right[index];
            Color rowColor = AppColors.softSheet;
            if (allAssigned) {
              rowColor = isCorrect
                  ? AppColors.mintLeaf.withValues(alpha: 0.18)
                  : AppColors.coralJam.withValues(alpha: 0.16);
            }
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: rowColor,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: <Widget>[
                    Expanded(child: Text(left[index])),
                    const SizedBox(width: AppSpacing.sm),
                    OutlinedButton(
                      onPressed: () => _cycleMatch(index),
                      child: Text(selection ?? '点此选择'),
                    ),
                    if (allAssigned) ...<Widget>[
                      const SizedBox(width: AppSpacing.xs),
                      Icon(
                        isCorrect
                            ? Icons.check_circle_rounded
                            : Icons.cancel_rounded,
                        color: isCorrect
                            ? AppColors.mintLeaf
                            : AppColors.coralJam,
                      ),
                    ],
                  ],
                ),
              ),
            );
          }),
          if (allAssigned) ...<Widget>[
            const SizedBox(height: AppSpacing.xs),
            Text(
              _matchSelections.length == right.length &&
                      _matchAllCorrect(right)
                  ? '全部答对啦！'
                  : '正确答案：${right.join('、')}',
              style: AppTextStyles.helper,
            ),
          ],
        ],
      ),
    );
  }

  bool _matchAllCorrect(List<String> right) {
    for (var i = 0; i < _matchSelections.length; i++) {
      if (i >= right.length || _matchSelections[i] != right[i]) {
        return false;
      }
    }
    return true;
  }

  void _cycleMatch(int index) {
    if (_shuffledRight.isEmpty) {
      return;
    }
    final current = _matchSelections[index];
    final currentIndex =
        current == null ? -1 : _shuffledRight.indexOf(current);
    final next = _shuffledRight[(currentIndex + 1) % _shuffledRight.length];
    setState(() => _matchSelections[index] = next);
    if (_matchSelections.every((e) => e != null)) {
      widget.onAnswer(PracticeTaskResult(
        taskId: widget.task.id,
        answers: _matchSelections.cast<String>(),
      ));
    }
  }
}

class _SelectableButton extends StatelessWidget {
  const _SelectableButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final Color color;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    if (selected) {
      return FilledButton.icon(
        onPressed: onPressed,
        style: FilledButton.styleFrom(backgroundColor: color),
        icon: Icon(icon),
        label: Text(label),
      );
    }
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

class _ReviewFinishedState extends StatelessWidget {
  const _ReviewFinishedState({required this.materialId, this.session});

  final String materialId;
  final PracticeSession? session;

  @override
  Widget build(BuildContext context) {
    final session = this.session;
    return SingleChildScrollView(
      child: Column(
        children: <Widget>[
          const IllustratedHeroCard(
            eyebrow: '完成啦',
            title: '这一轮复习已经收进本周成长记录里',
            description: '现在可以继续做口语问答，也可以切到亲子陪练，让家长跟着提示再陪孩子说一轮。',
            accent: AppColors.mintLeaf,
            illustration: Icons.workspace_premium_rounded,
            assetPath: AppIllustrations.stateSuccess,
            badge:
                StickerBadge(label: 'Good job', icon: Icons.celebration_rounded),
          ),
          const SizedBox(height: AppSpacing.md),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('本次复习完成', style: AppTextStyles.pageTitle),
                const SizedBox(height: AppSpacing.sm),
                if (session != null) ...<Widget>[
                  Text('本次得分 ${session.score.round()} 分',
                      style: AppTextStyles.sectionTitle),
                  const SizedBox(height: AppSpacing.xs),
                  if (session.weakPoints.isNotEmpty)
                    Text('还需加强：${session.weakPoints.join('、')}',
                        style: AppTextStyles.helper)
                  else
                    Text('全部答对，太棒了！', style: AppTextStyles.helper),
                ] else
                  const Text('已经记录完成情况，接下来可以继续做口语问答或亲子陪练。'),
                const SizedBox(height: AppSpacing.md),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  children: <Widget>[
                    FilledButton(
                      onPressed: () =>
                          context.push('/review/speaking/$materialId'),
                      child: const Text('继续口语陪练'),
                    ),
                    OutlinedButton(
                      onPressed: () =>
                          context.push('/review/coaching/$materialId'),
                      child: const Text('进入亲子陪练'),
                    ),
                    OutlinedButton(
                      onPressed: () => context.go('/lessons/$materialId'),
                      child: const Text('回到本课'),
                    ),
                    TextButton(
                      onPressed: () => context.go('/reports'),
                      child: const Text('查看本周报告'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _taskAsset(ReviewTask task) {
  final word = task.contentJson['word'] as String?;
  if (word != null) {
    return AppIllustrations.vocabularyFor(word) ?? AppIllustrations.heroLesson;
  }
  switch (task.taskType) {
    case TaskType.flashcard:
      return AppIllustrations.heroLesson;
    case TaskType.listenChoice:
      return AppIllustrations.heroSpeakingPartner;
    case TaskType.matchChoice:
      return AppIllustrations.topicDialogue;
    case TaskType.speakingPrompt:
      return AppIllustrations.heroSpeakingPartner;
    case TaskType.parentCoaching:
      return AppIllustrations.heroParentCoaching;
  }
}

Color _taskAccent(TaskType type) {
  switch (type) {
    case TaskType.flashcard:
      return AppColors.skyBlue;
    case TaskType.listenChoice:
      return AppColors.butterYellow;
    case TaskType.matchChoice:
      return AppColors.mintLeaf;
    case TaskType.speakingPrompt:
      return AppColors.skyBlue;
    case TaskType.parentCoaching:
      return AppColors.coralJam;
  }
}

IconData _taskIcon(TaskType type) {
  switch (type) {
    case TaskType.flashcard:
      return Icons.style_rounded;
    case TaskType.listenChoice:
      return Icons.headphones_rounded;
    case TaskType.matchChoice:
      return Icons.extension_rounded;
    case TaskType.speakingPrompt:
      return Icons.mic_rounded;
    case TaskType.parentCoaching:
      return Icons.favorite_rounded;
  }
}
