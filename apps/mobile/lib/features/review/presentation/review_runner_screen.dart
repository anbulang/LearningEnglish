import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/analytics/app_analytics.dart';
import '../../../core/widgets/app_card.dart';
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
            final tasks = items.where((task) => task.materialId == widget.materialId).toList();
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
                      if (_currentIndex + 1 == tasks.length && !_sessionRecorded) {
                        await ref.read(appRepositoryProvider).createPracticeSession(
                              childId: child.id,
                              reviewTaskIds: tasks.map((task) => task.id).toList(),
                              score: 92,
                              weakPoints: const <String>['bird'],
                            );
                        ref.invalidate(reviewTasksProvider);
                        ref.invalidate(weeklyReportProvider);
                        ref.read(appAnalyticsProvider).track('review_session_completed', {
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
            description: error.toString(),
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
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('任务 ${currentIndex + 1} / $totalCount', style: AppTextStyles.helper),
              const SizedBox(height: AppSpacing.xs),
              LinearProgressIndicator(
                value: (currentIndex + 1) / totalCount,
                minHeight: 8,
                borderRadius: BorderRadius.circular(AppRadii.pill),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(task.contentJson['prompt'] as String? ?? '复习任务', style: AppTextStyles.pageTitle),
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
        return AppCard(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            children: <Widget>[
              Text(task.contentJson['word'] as String? ?? '', style: AppTextStyles.pageTitle),
              const SizedBox(height: AppSpacing.sm),
              Text(task.contentJson['hint'] as String? ?? '点击播放音频并跟读'),
              const SizedBox(height: AppSpacing.md),
              const Icon(Icons.volume_up_rounded, size: 48),
            ],
          ),
        );
      case TaskType.listenChoice:
        final choices =
            List<String>.from(task.contentJson['choices'] as List<dynamic>? ?? const <String>[]);
        return Column(
          children: choices
              .map(
                (choice) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: AppCard(
                    child: ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.hearing_rounded),
                      title: Text(choice),
                    ),
                  ),
                ),
              )
              .toList(),
        );
      case TaskType.matchChoice:
        final left =
            List<String>.from(task.contentJson['left'] as List<dynamic>? ?? const <String>[]);
        final right =
            List<String>.from(task.contentJson['right'] as List<dynamic>? ?? const <String>[]);
        return AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              ...left.map((item) => Text('Q: $item')),
              const SizedBox(height: AppSpacing.md),
              ...right.map((item) => Text('A: $item')),
            ],
          ),
        );
      case TaskType.speakingPrompt:
      case TaskType.parentCoaching:
        return AppCard(child: Text(task.contentJson['prompt'] as String? ?? '任务'));
    }
  }
}

class _ReviewFinishedState extends StatelessWidget {
  const _ReviewFinishedState({required this.materialId});

  final String materialId;

  @override
  Widget build(BuildContext context) {
    return AppCard(
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
    );
  }
}
