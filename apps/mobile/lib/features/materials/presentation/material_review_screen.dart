import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
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
  ConsumerState<MaterialReviewScreen> createState() =>
      _MaterialReviewScreenState();
}

class _MaterialReviewScreenState extends ConsumerState<MaterialReviewScreen> {
  bool _submitting = false;
  String? _actionError;

  Future<void> _confirm(MaterialParseJob job) async {
    final router = GoRouter.of(context);
    setState(() {
      _submitting = true;
      _actionError = null;
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
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _actionError = describeApiError(error, fallback: '生成课程详情失败，请稍后重试。');
      });
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  Future<void> _retryJob() async {
    setState(() {
      _submitting = true;
      _actionError = null;
    });
    try {
      await ref
          .read(appRepositoryProvider)
          .retryMaterialJob(jobId: widget.jobId);
      ref.invalidate(materialJobProvider(widget.jobId));
      ref.invalidate(materialsProvider);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _actionError = describeApiError(error, fallback: '重试失败，请稍后再试。');
      });
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final jobAsync = ref.watch(materialJobProvider(widget.jobId));
    final formFactor = formFactorOf(context);

    final extracted = jobAsync.when(
      data: (job) {
        if (job.status == JobStatus.processing ||
            job.status == JobStatus.queued) {
          return Column(
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: 'AI 理解中',
                title: '讲义正在慢慢变成可复习的小课包',
                description: '系统会先识别课题、单词和句型，再交给家长确认。这个阶段只需要稍后刷新看结果。',
                accent: AppColors.skyBlue,
                illustration: Icons.psychology_alt_rounded,
                assetPath: AppIllustrations.heroAiProcessing,
                badge: StickerBadge(
                    label: '处理中',
                    icon: Icons.hourglass_top_rounded,
                    color: AppColors.skyBlue),
              ),
              const SizedBox(height: AppSpacing.md),
              StatePanel(
                title: 'AI 正在处理中',
                description: '讲义已上传成功，正在提取单词和句型。稍后刷新即可查看结果。',
                assetPath: AppIllustrations.heroAiProcessing,
                action: FilledButton(
                  onPressed: _submitting
                      ? null
                      : () => ref.invalidate(materialJobProvider(widget.jobId)),
                  child: const Text('刷新结果'),
                ),
              ),
            ],
          );
        }
        if (job.status == JobStatus.ready) {
          return Column(
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: '已准备好',
                title: '课程详情已经整理完成，可以直接开始复习了',
                description: '本课知识包已经生成，接下来可以进入课程详情、词卡练习、口语陪练和亲子陪练。',
                accent: AppColors.mintLeaf,
                illustration: Icons.check_circle_rounded,
                assetPath: AppIllustrations.heroAiReady,
                badge: StickerBadge(
                    label: '可复习',
                    icon: Icons.auto_awesome_rounded,
                    color: AppColors.mintLeaf),
              ),
              const SizedBox(height: AppSpacing.md),
              StatePanel(
                title: '课程详情已生成',
                description: '本课知识包已经准备好，可以直接进入课程详情开始复习。',
                assetPath: AppIllustrations.stateSuccess,
                action: FilledButton(
                  onPressed: () => context.go('/lessons/${widget.materialId}'),
                  child: const Text('查看课程详情'),
                ),
              ),
            ],
          );
        }
        if (job.status == JobStatus.failed) {
          return Column(
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: '需要重试',
                title: '这次理解讲义时卡住了，再试一次就好',
                description: '真实讲义有时会因为图片质量或排版复杂而失败。你可以直接重新处理。',
                accent: AppColors.coralJam,
                illustration: Icons.refresh_rounded,
                assetPath: AppIllustrations.heroAiRetry,
                badge: StickerBadge(
                    label: '可重试',
                    icon: Icons.replay_rounded,
                    color: AppColors.errorSurface),
              ),
              const SizedBox(height: AppSpacing.md),
              StatePanel(
                title: 'AI 处理失败',
                description: _recognitionFailureMessage(job, _actionError),
                icon: Icons.error_outline_rounded,
                assetPath: AppIllustrations.stateError,
                action: FilledButton(
                  onPressed: _submitting ? null : _retryJob,
                  child: Text(_submitting ? '重试中...' : '重新识别'),
                ),
              ),
            ],
          );
        }
        return AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: '家长校对',
                title: 'AI 已经整理出草稿，你看一眼就能生成正式课程详情',
                description: '先确认标题、主题、词汇和句型。低置信度内容会用提醒样式突出显示。',
                accent: AppColors.coralJam,
                illustration: Icons.fact_check_rounded,
                assetPath: AppIllustrations.heroAiReady,
                badge:
                    StickerBadge(label: '审核确认', icon: Icons.edit_note_rounded),
              ),
              const SizedBox(height: AppSpacing.md),
              Text('AI 识别结果', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              Text('课程标题：${job.draftTitle}'),
              Text('主题：${job.draftTopic}'),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: const <Widget>[
                  Text('词汇', style: AppTextStyles.cardTitle),
                  SizedBox(width: AppSpacing.sm),
                  StickerBadge(label: '词卡候选', color: AppColors.skyBlue),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              if (job.draftVocabulary.isEmpty)
                const Text('暂未提取到词汇，请家长确认后继续。')
              else
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: job.draftVocabulary
                      .map(
                        (word) => Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.sm,
                            vertical: AppSpacing.xs,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.skyBlue.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(AppRadii.pill),
                          ),
                          child: Text(word),
                        ),
                      )
                      .toList(),
                ),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: const <Widget>[
                  Text('句型', style: AppTextStyles.cardTitle),
                  SizedBox(width: AppSpacing.sm),
                  StickerBadge(label: '跟读候选', color: AppColors.butterYellow),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              if (job.draftSentences.isEmpty)
                const Text('暂未提取到句型，请家长确认后继续。')
              else
                ...job.draftSentences.map(
                  (sentence) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: Container(
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      decoration: BoxDecoration(
                        color: AppColors.softSheet,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Row(
                        children: <Widget>[
                          const Icon(Icons.subtitles_rounded,
                              color: AppColors.cocoaCoral),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(child: Text(sentence)),
                        ],
                      ),
                    ),
                  ),
                ),
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
              if (_actionError != null) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                StatePanel(
                  title: '操作失败',
                  description: _actionError!,
                  icon: Icons.error_outline_rounded,
                  assetPath: AppIllustrations.stateError,
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: <Widget>[
                  FilledButton(
                    onPressed: _submitting ? null : () => _confirm(job),
                    child: Text(_submitting ? '生成中...' : '确认并生成课程详情'),
                  ),
                  OutlinedButton(
                    onPressed: _submitting ? null : _retryJob,
                    child: const Text('重新处理'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => StatePanel(
        title: 'AI 校对加载失败',
        description: describeApiError(error, fallback: '校对结果暂时不可用，请稍后重试。'),
        assetPath: AppIllustrations.stateError,
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
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const <Widget>[
                          ClipRRect(
                            borderRadius: BorderRadius.all(Radius.circular(28)),
                            child: Image(
                              image: AssetImage(AppIllustrations.heroUpload),
                              width: 148,
                              height: 148,
                              fit: BoxFit.cover,
                            ),
                          ),
                          SizedBox(height: AppSpacing.sm),
                          Text('原始讲义预览'),
                        ],
                      ),
                    ),
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

String _recognitionFailureMessage(MaterialParseJob job, String? actionError) {
  final message = actionError ?? job.confidenceSummary;
  if (message.toLowerCase().contains('timeout')) {
    return '识别超时，请确认网络稳定后重新识别。原始讲义已经保留，不需要重新上传。';
  }
  if (message.trim().isEmpty) {
    return '识别失败，请重新识别。原始讲义已经保留，不需要重新上传。';
  }
  return message;
}
