import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';
import '../data/app_repository.dart';

class MaterialReviewScreen extends ConsumerStatefulWidget {
  const MaterialReviewScreen({
    required this.jobId,
    required this.materialId,
    super.key,
  });

  final String jobId;
  final String materialId;

  @override
  ConsumerState<MaterialReviewScreen> createState() => _MaterialReviewScreenState();
}

class _MaterialReviewScreenState extends ConsumerState<MaterialReviewScreen> {
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    final jobAsync = ref.watch(materialJobProvider(widget.jobId));
    final formFactor = formFactorOf(context);

    final extracted = jobAsync.when(
      data: (job) => AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('AI 识别结果', style: AppTextStyles.sectionTitle),
            const SizedBox(height: AppSpacing.sm),
            Text('课程标题：${job.draftTitle}'),
            Text('主题：${job.draftTopic}'),
            const SizedBox(height: AppSpacing.md),
            Text('词汇', style: AppTextStyles.cardTitle),
            const SizedBox(height: AppSpacing.xs),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: job.draftVocabulary.map((word) => Chip(label: Text(word))).toList(),
            ),
            const SizedBox(height: AppSpacing.md),
            Text('句型', style: AppTextStyles.cardTitle),
            const SizedBox(height: AppSpacing.xs),
            ...job.draftSentences.map((sentence) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.subtitles_rounded),
                  title: Text(sentence),
                )),
            if (job.warnings.isNotEmpty) ...<Widget>[
              const SizedBox(height: AppSpacing.md),
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.errorSurface,
                  borderRadius: BorderRadius.circular(AppRadii.card),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('需要家长确认', style: AppTextStyles.cardTitle),
                    const SizedBox(height: AppSpacing.xs),
                    ...job.warnings.map((item) => Text('• $item')),
                  ],
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            FilledButton(
              onPressed: _submitting
                  ? null
                  : () async {
                      final router = GoRouter.of(context);
                      setState(() {
                        _submitting = true;
                      });
                      try {
                        await ref.read(appRepositoryProvider).confirmMaterialJob(
                              jobId: widget.jobId,
                              draftTitle: job.draftTitle,
                              draftTopic: job.draftTopic,
                              draftVocabulary: job.draftVocabulary,
                              draftSentences: job.draftSentences,
                            );
                        ref.invalidate(materialProvider(widget.materialId));
                        ref.invalidate(materialsProvider);
                        ref.invalidate(reviewTasksProvider);
                        if (!mounted) {
                          return;
                        }
                        router.go('/lessons/${widget.materialId}');
                      } finally {
                        if (mounted) {
                          setState(() {
                            _submitting = false;
                          });
                        }
                      }
                    },
              child: Text(_submitting ? '生成中...' : '确认并生成课程详情'),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => StatePanel(
        title: 'AI 校对加载失败',
        description: error.toString(),
        action: FilledButton(
          onPressed: () => ref.invalidate(materialJobProvider(widget.jobId)),
          child: const Text('重试'),
        ),
      ),
    );

    if (!formFactor.isTablet) {
      return Scaffold(
        appBar: AppBar(title: const Text('AI 校对')),
        body: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: <Widget>[extracted],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('AI 校对')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppCard(
                child: AspectRatio(
                  aspectRatio: 3 / 4,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: AppColors.softSheet,
                      borderRadius: BorderRadius.circular(AppRadii.card),
                    ),
                    child: const Center(child: Text('原始讲义预览')),
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(child: extracted),
          ],
        ),
      ),
    );
  }
}
