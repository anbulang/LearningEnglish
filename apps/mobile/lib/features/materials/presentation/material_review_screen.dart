import 'dart:async';

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
import '../../../core/widgets/remote_asset_image.dart';
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
  static const _pollInterval = Duration(seconds: 3);

  bool _submitting = false;
  String? _actionError;
  Timer? _pollTimer;

  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _topicController = TextEditingController();
  final List<String> _vocabulary = <String>[];
  final List<String> _sentences = <String>[];
  String? _editingJobId;

  @override
  void dispose() {
    _pollTimer?.cancel();
    _titleController.dispose();
    _topicController.dispose();
    super.dispose();
  }

  /// Seeds the editable fields from [job] once per job so parent edits survive
  /// provider rebuilds.
  void _ensureEditingState(MaterialParseJob job) {
    if (_editingJobId == job.id) {
      return;
    }
    _editingJobId = job.id;
    _titleController.text = job.draftTitle;
    _topicController.text = job.draftTopic;
    _vocabulary
      ..clear()
      ..addAll(job.draftVocabulary);
    _sentences
      ..clear()
      ..addAll(job.draftSentences);
  }

  Future<String?> _promptForText({
    required String title,
    String initial = '',
  }) async {
    final controller = TextEditingController(text: initial);
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(border: OutlineInputBorder()),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(dialogContext).pop(controller.text.trim()),
            child: const Text('保存'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _addVocabulary() async {
    final value = await _promptForText(title: '添加单词');
    if (!mounted || value == null || value.isEmpty) {
      return;
    }
    setState(() => _vocabulary.add(value));
  }

  Future<void> _editVocabulary(int index) async {
    final value =
        await _promptForText(title: '修改单词', initial: _vocabulary[index]);
    if (!mounted || value == null) {
      return;
    }
    setState(() {
      if (value.isEmpty) {
        _vocabulary.removeAt(index);
      } else {
        _vocabulary[index] = value;
      }
    });
  }

  void _removeVocabulary(int index) {
    setState(() => _vocabulary.removeAt(index));
  }

  Future<void> _addSentence() async {
    final value = await _promptForText(title: '添加句子');
    if (!mounted || value == null || value.isEmpty) {
      return;
    }
    setState(() => _sentences.add(value));
  }

  Future<void> _editSentence(int index) async {
    final value =
        await _promptForText(title: '修改句子', initial: _sentences[index]);
    if (!mounted || value == null) {
      return;
    }
    setState(() {
      if (value.isEmpty) {
        _sentences.removeAt(index);
      } else {
        _sentences[index] = value;
      }
    });
  }

  void _removeSentence(int index) {
    setState(() => _sentences.removeAt(index));
  }

  void _syncPolling(JobStatus status) {
    final shouldPoll =
        status == JobStatus.processing || status == JobStatus.queued;
    if (!shouldPoll) {
      _pollTimer?.cancel();
      _pollTimer = null;
      return;
    }
    if (_pollTimer?.isActive ?? false) {
      return;
    }
    _pollTimer = Timer(_pollInterval, () {
      _pollTimer = null;
      if (!mounted) {
        return;
      }
      ref.invalidate(materialJobProvider(widget.jobId));
    });
  }

  Future<void> _confirm(MaterialParseJob job) async {
    final router = GoRouter.of(context);
    setState(() {
      _submitting = true;
      _actionError = null;
    });
    try {
      await ref.read(appRepositoryProvider).confirmMaterialJob(
            jobId: widget.jobId,
            draftTitle: _titleController.text.trim(),
            draftTopic: _topicController.text.trim(),
            draftVocabulary: List<String>.of(_vocabulary),
            draftSentences: List<String>.of(_sentences),
          );
      ref.invalidate(materialProvider(widget.materialId));
      ref.invalidate(knowledgePackProvider(widget.materialId));
      ref.invalidate(parentCoachingScriptProvider(widget.materialId));
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
    if (_editingJobId != null) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('重新处理讲义？'),
          content: const Text('会重新识别讲义并清空你当前的修改。'),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('重新处理'),
            ),
          ],
        ),
      );
      if (!mounted || confirmed != true) {
        return;
      }
    }
    setState(() {
      _submitting = true;
      _actionError = null;
    });
    try {
      await ref
          .read(appRepositoryProvider)
          .retryMaterialJob(jobId: widget.jobId);
      // Re-seed the editor from the freshly re-identified draft next time.
      _editingJobId = null;
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
        _syncPolling(job.status);
        if (job.status == JobStatus.processing ||
            job.status == JobStatus.queued) {
          return Column(
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: 'AI 理解中',
                title: '讲义正在慢慢变成可复习的小课包',
                description: '系统会先识别课题、单词和句型，再交给家长确认。页面会自动刷新处理结果。',
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
                description: '讲义已上传成功，正在提取单词和句型。处理完成后会自动进入校对内容。',
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
        _ensureEditingState(job);
        return AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const IllustratedHeroCard(
                eyebrow: '家长校对',
                title: 'AI 已经整理出草稿，确认或修改后即可生成正式课程详情',
                description: '可以直接改正识别错误的标题、主题、词汇和句型，再生成课程。',
                accent: AppColors.coralJam,
                illustration: Icons.fact_check_rounded,
                assetPath: AppIllustrations.heroAiReady,
                badge:
                    StickerBadge(label: '审核确认', icon: Icons.edit_note_rounded),
              ),
              const SizedBox(height: AppSpacing.md),
              Text('AI 识别结果', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              TextField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: '课程标题',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              TextField(
                controller: _topicController,
                decoration: const InputDecoration(
                  labelText: '主题',
                  border: OutlineInputBorder(),
                ),
              ),
              if (job.draftImageRecords.isNotEmpty) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                _ImageRecordsSection(records: job.draftImageRecords),
              ],
              if (job.draftLearningAssets.isNotEmpty) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                _LearningAssetsSection(
                  assets: job.draftLearningAssets,
                  imageRecords: job.draftImageRecords,
                ),
              ],
              const SizedBox(height: AppSpacing.md),
              Row(
                children: const <Widget>[
                  Text('词汇', style: AppTextStyles.cardTitle),
                  SizedBox(width: AppSpacing.sm),
                  StickerBadge(label: '词卡候选', color: AppColors.skyBlue),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Text('点词条可修改，× 删除识别错误的词。', style: AppTextStyles.helper),
              const SizedBox(height: AppSpacing.xs),
              Wrap(
                spacing: AppSpacing.xs,
                runSpacing: AppSpacing.xs,
                children: <Widget>[
                  for (var i = 0; i < _vocabulary.length; i++)
                    InputChip(
                      label: Text(_vocabulary[i]),
                      onPressed: () => _editVocabulary(i),
                      onDeleted: () => _removeVocabulary(i),
                      deleteIcon: const Icon(Icons.close_rounded, size: 18),
                      deleteButtonTooltipMessage: '删除这个词',
                      backgroundColor: AppColors.skyBlue.withValues(alpha: 0.18),
                    ),
                  ActionChip(
                    avatar: const Icon(Icons.add_rounded, size: 18),
                    label: const Text('添加单词'),
                    onPressed: _addVocabulary,
                  ),
                ],
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
              Text('点句子可修改文本，× 删除。', style: AppTextStyles.helper),
              const SizedBox(height: AppSpacing.xs),
              for (var i = 0; i < _sentences.length; i++)
                Padding(
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
                        Expanded(
                          child: InkWell(
                            onTap: () => _editSentence(i),
                            child: Text(_sentences[i]),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded, size: 18),
                          tooltip: '删除这句',
                          onPressed: () => _removeSentence(i),
                        ),
                      ],
                    ),
                  ),
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _addSentence,
                  icon: const Icon(Icons.add_rounded),
                  label: const Text('添加句子'),
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

class _ImageRecordsSection extends StatelessWidget {
  const _ImageRecordsSection({required this.records});

  final List<MaterialImageRecord> records;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: const <Widget>[
            Text('图片记录', style: AppTextStyles.cardTitle),
            SizedBox(width: AppSpacing.sm),
            StickerBadge(label: '逐页保留', color: AppColors.mintLeaf),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ...records.map(
          (record) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: AppColors.softSheet,
                borderRadius: BorderRadius.circular(AppRadii.card),
              ),
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.sm),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Text('第 ${record.pageIndex} 页',
                            style: AppTextStyles.cardTitle),
                        const SizedBox(width: AppSpacing.sm),
                        Text(_sourceLabel(record.sourceType),
                            style: AppTextStyles.helper),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Text(record.imageTitle.isEmpty
                        ? record.originalFilename
                        : record.imageTitle),
                    if (record.vocabulary.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xs),
                      Text('单词：${record.vocabulary.join('、')}',
                          style: AppTextStyles.helper),
                    ],
                    if (record.sentences.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xs),
                      Text('句子：${record.sentences.join(' / ')}',
                          style: AppTextStyles.helper),
                    ],
                    if (record.details.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xs),
                      Text('细节：${record.details.join('；')}',
                          style: AppTextStyles.helper),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LearningAssetsSection extends StatelessWidget {
  const _LearningAssetsSection({
    required this.assets,
    required this.imageRecords,
  });

  final List<LearningAsset> assets;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: const <Widget>[
            Text('核心学习资产', style: AppTextStyles.cardTitle),
            SizedBox(width: AppSpacing.sm),
            StickerBadge(label: '1-20 个', color: AppColors.butterYellow),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ...assets.map(
          (asset) => _LearningAssetReviewTile(
            asset: asset,
            imageRecords: imageRecords,
          ),
        ),
      ],
    );
  }
}

class _LearningAssetReviewTile extends StatelessWidget {
  const _LearningAssetReviewTile({
    required this.asset,
    required this.imageRecords,
  });

  final LearningAsset asset;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.softSheet,
          borderRadius: BorderRadius.circular(AppRadii.card),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _SourceCropPreview(asset: asset, imageRecords: imageRecords),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(asset.text, style: AppTextStyles.cardTitle),
                    if (asset.translation.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xxs),
                      Text(asset.translation),
                    ],
                    const SizedBox(height: AppSpacing.xxs),
                    Text(
                      '${_assetKindLabel(asset.kind)} · 第 ${asset.sourcePageIndex} 页',
                      style: AppTextStyles.helper,
                    ),
                    if (asset.teachingNote.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xxs),
                      Text(asset.teachingNote, style: AppTextStyles.helper),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SourceCropPreview extends StatelessWidget {
  const _SourceCropPreview({
    required this.asset,
    required this.imageRecords,
  });

  final LearningAsset asset;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    final record = _recordForPage();
    if (record == null || record.url.isEmpty) {
      return _CropPlaceholder(
        icon: Icons.crop_rounded,
        label: '第 ${asset.sourcePageIndex} 页',
      );
    }
    final bbox = asset.sourceBbox;
    if (bbox == null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadii.input),
        child: RemoteAssetImage(
          url: record.url,
          width: 72,
          height: 72,
          errorIcon: Icons.image_not_supported_outlined,
        ),
      );
    }
    final width = _boundedFraction(bbox.width, minimum: 0.05);
    final height = _boundedFraction(bbox.height, minimum: 0.05);
    final x = _boundedFraction(bbox.x);
    final y = _boundedFraction(bbox.y);
    final scaledWidth = 72 / width;
    final scaledHeight = 72 / height;
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.input),
      child: SizedBox(
        width: 72,
        height: 72,
        child: ClipRect(
          child: OverflowBox(
            alignment: Alignment.topLeft,
            minWidth: scaledWidth,
            maxWidth: scaledWidth,
            minHeight: scaledHeight,
            maxHeight: scaledHeight,
            child: Transform.translate(
              offset: Offset(-x * scaledWidth, -y * scaledHeight),
              child: RemoteAssetImage(
                url: record.url,
                width: scaledWidth,
                height: scaledHeight,
                fit: BoxFit.fill,
                errorIcon: Icons.image_not_supported_outlined,
              ),
            ),
          ),
        ),
      ),
    );
  }

  MaterialImageRecord? _recordForPage() {
    for (final record in imageRecords) {
      if (record.pageIndex == asset.sourcePageIndex) {
        return record;
      }
    }
    return null;
  }
}

class _CropPlaceholder extends StatelessWidget {
  const _CropPlaceholder({required this.icon, this.label});

  final IconData icon;
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 72,
      height: 72,
      decoration: BoxDecoration(
        color: AppColors.paperWhite,
        borderRadius: BorderRadius.circular(AppRadii.input),
      ),
      alignment: Alignment.center,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, color: AppColors.cocoaCoral),
          if (label != null) ...<Widget>[
            const SizedBox(height: AppSpacing.xxs),
            Text(label!, style: AppTextStyles.helper),
          ],
        ],
      ),
    );
  }
}

double _boundedFraction(double value,
    {double minimum = 0, double maximum = 1}) {
  return value.clamp(minimum, maximum).toDouble();
}

String _assetKindLabel(String kind) {
  return switch (kind) {
    'sentence' => '句子',
    'phrase' => '短语',
    _ => '单词',
  };
}

String _sourceLabel(String sourceType) {
  return sourceType == 'camera' ? '相机拍摄' : '相册选择';
}
