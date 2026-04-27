import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/analytics/app_analytics.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
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
            if (tasks.isEmpty || child == null) {
              return const Center(child: Text('当前没有可进行的复习任务'));
            }
            final isFinished = _currentIndex >= tasks.length;
            return isFinished
                ? _ReviewFinishedState(materialId: widget.materialId)
                : _ReviewTaskStage(
                    task: tasks[_currentIndex],
                    currentIndex: _currentIndex,
                    totalCount: tasks.length,
                    onNext: () async {
                      if (_currentIndex + 1 == tasks.length &&
                          !_sessionRecorded) {
                        await ref
                            .read(appRepositoryProvider)
                            .createPracticeSession(
                          childId: child.id,
                          reviewTaskIds: tasks.map((task) => task.id).toList(),
                          score: 92,
                          weakPoints: const <String>['bird'],
                        );
                        ref.invalidate(reviewTasksProvider);
                        ref.invalidate(weeklyReportProvider);
                        ref
                            .read(appAnalyticsProvider)
                            .track('review_session_completed', {
                          'materialId': widget.materialId,
                          'taskCount': tasks.length,
                        });
                        _sessionRecorded = true;
                      }
                      if (mounted) {
                        setState(() {
                          _currentIndex += 1;
                        });
                      }
                    },
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
}

class _ReviewTaskStage extends StatelessWidget {
  const _ReviewTaskStage({
    required this.task,
    required this.currentIndex,
    required this.totalCount,
    required this.onNext,
  });

  final ReviewTask task;
  final int currentIndex;
  final VoidCallback onNext;
  final int totalCount;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        IllustratedHeroCard(
          eyebrow: '复习进行中',
          title: task.contentJson['prompt'] as String? ?? '复习任务',
          description: '第 ${currentIndex + 1} 题，共 $totalCount 题。一步一步完成就好。',
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
              _TaskSurface(task: task),
            ],
          ),
        ),
        const Spacer(),
        Align(
          alignment: Alignment.bottomRight,
          child: FilledButton(
            onPressed: onNext,
            child: Text(currentIndex + 1 == totalCount ? '完成本次复习' : '继续下一题'),
          ),
        ),
      ],
    );
  }
}

class _TaskSurface extends StatelessWidget {
  const _TaskSurface({required this.task});

  final ReviewTask task;

  @override
  Widget build(BuildContext context) {
    switch (task.taskType) {
      case TaskType.flashcard:
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
              const Icon(Icons.volume_up_rounded, size: 48),
            ],
          ),
        );
      case TaskType.listenChoice:
        final choices = List<String>.from(
            task.contentJson['choices'] as List<dynamic>? ?? const <String>[]);
        return Column(
          children: choices
              .map(
                (choice) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: AppCard(
                    child: ListTile(
                      contentPadding: EdgeInsets.zero,
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
                    ),
                  ),
                ),
              )
              .toList(),
        );
      case TaskType.matchChoice:
        final left = List<String>.from(
            task.contentJson['left'] as List<dynamic>? ?? const <String>[]);
        final right = List<String>.from(
            task.contentJson['right'] as List<dynamic>? ?? const <String>[]);
        return AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              ...left.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                  child: Container(
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    decoration: BoxDecoration(
                      color: AppColors.softSheet,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text('Q: $item'),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              ...right.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                  child: Container(
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    decoration: BoxDecoration(
                      color: AppColors.mintLeaf.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text('A: $item'),
                  ),
                ),
              ),
            ],
          ),
        );
      case TaskType.speakingPrompt:
      case TaskType.parentCoaching:
        return AppCard(
            child: Text(task.contentJson['prompt'] as String? ?? '任务'));
    }
  }
}

class _ReviewFinishedState extends StatelessWidget {
  const _ReviewFinishedState({required this.materialId});

  final String materialId;

  @override
  Widget build(BuildContext context) {
    return Column(
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
              const Text('已经记录完成情况，接下来可以继续做口语问答或亲子陪练。'),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: <Widget>[
                  FilledButton(
                    onPressed: () => context.go('/review/speaking/$materialId'),
                    child: const Text('继续口语陪练'),
                  ),
                  OutlinedButton(
                    onPressed: () => context.go('/review/coaching/$materialId'),
                    child: const Text('进入亲子陪练'),
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
