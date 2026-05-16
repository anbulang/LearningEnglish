import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';

class LessonDetailScreen extends ConsumerWidget {
  const LessonDetailScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final materialAsync = ref.watch(materialProvider(materialId));
    final knowledgeAsync = ref.watch(knowledgePackProvider(materialId));
    final formFactor = formFactorOf(context);

    final detailContent = materialAsync.when(
      data: (material) => knowledgeAsync.when(
        data: (knowledge) => ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: <Widget>[
            IllustratedHeroCard(
              eyebrow: '本课复习包',
              title: material.title,
              description:
                  '${material.teacherName} · ${material.lessonDate.month}/${material.lessonDate.day} · ${material.topic}\n\n${knowledge.lessonSummary}',
              accent: _lessonAccent(material.topic),
              illustration: _lessonIcon(material.topic),
              assetPath: AppIllustrations.topicFor(material.topic),
              badge: const StickerBadge(
                  label: '可开练',
                  icon: Icons.check_circle_rounded,
                  color: AppColors.mintLeaf),
            ),
            if (material.imageRecords.isNotEmpty) ...<Widget>[
              const SizedBox(height: AppSpacing.md),
              _SourceImagesCard(records: material.imageRecords),
            ],
            if (material.learningAssets.isNotEmpty) ...<Widget>[
              const SizedBox(height: AppSpacing.md),
              _LearningAssetsCard(
                materialId: material.id,
                assets: material.learningAssets,
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Text('核心单词', style: AppTextStyles.sectionTitle),
                      const SizedBox(width: AppSpacing.sm),
                      const StickerBadge(
                          label: '词卡包', color: AppColors.skyBlue),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: knowledge.vocabularyItems
                        .map(
                          (item) => Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.sm,
                              vertical: AppSpacing.sm,
                            ),
                            decoration: BoxDecoration(
                              color: Color.alphaBlend(
                                _lessonAccent(material.topic)
                                    .withValues(alpha: 0.12),
                                AppColors.paperWhite,
                              ),
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Text('${item.word} · ${item.meaningCn}',
                                style: AppTextStyles.body),
                          ),
                        )
                        .toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Text('重点句型', style: AppTextStyles.sectionTitle),
                      const SizedBox(width: AppSpacing.sm),
                      const StickerBadge(
                          label: '跟读句型', color: AppColors.butterYellow),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  ...knowledge.sentencePatterns.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.softSheet,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(item.sentence, style: AppTextStyles.cardTitle),
                            const SizedBox(height: AppSpacing.xs),
                            Text(item.meaningCn),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: <Widget>[
                      FilledButton.icon(
                        onPressed: () =>
                            context.go('/review/session/$materialId'),
                        icon: const Icon(Icons.play_arrow_rounded),
                        label: const Text('开始本课复习'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () =>
                            context.go('/review/speaking/$materialId'),
                        icon: const Icon(Icons.mic_none_rounded),
                        label: const Text('口语陪练'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () =>
                            context.go('/review/coaching/$materialId'),
                        icon: const Icon(Icons.favorite_border_rounded),
                        label: const Text('亲子陪练'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => StatePanel(
          title: '课程内容暂未就绪',
          description:
              describeApiError(error, fallback: '知识包还没有准备好，请稍后刷新或回到资料库查看处理状态。'),
          assetPath: AppIllustrations.stateEmpty,
          action: Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton(
                onPressed: () =>
                    ref.invalidate(knowledgePackProvider(materialId)),
                child: const Text('刷新'),
              ),
              OutlinedButton(
                onPressed: () => context.go('/materials'),
                child: const Text('回到资料库'),
              ),
            ],
          ),
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) {
        final notFound = isNotFoundApiError(error);
        return StatePanel(
          title: notFound ? '课程资料不存在或已删除' : '课程详情加载失败',
          description: notFound
              ? '这份课程资料可能已经被删除，请回到资料库查看最新列表。'
              : describeApiError(error, fallback: '课程详情加载失败，请稍后重试。'),
          assetPath: AppIllustrations.stateError,
          action: notFound
              ? OutlinedButton(
                  onPressed: () => context.go('/materials'),
                  child: const Text('回到资料库'),
                )
              : FilledButton(
                  onPressed: () => ref.invalidate(materialProvider(materialId)),
                  child: const Text('重新加载'),
                ),
        );
      },
    );

    if (!formFactor.isTablet) {
      return Scaffold(
          appBar: AppBar(title: const Text('课程详情')), body: detailContent);
    }

    return Scaffold(
      appBar: AppBar(title: const Text('课程详情')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('原始讲义', style: AppTextStyles.sectionTitle),
                    const SizedBox(height: AppSpacing.sm),
                    Expanded(
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
                                borderRadius:
                                    BorderRadius.all(Radius.circular(28)),
                                child: Image(
                                  image:
                                      AssetImage(AppIllustrations.heroLesson),
                                  width: 148,
                                  height: 148,
                                  fit: BoxFit.cover,
                                ),
                              ),
                              SizedBox(height: AppSpacing.sm),
                              Text('Worksheet / PDF Preview'),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(flex: 2, child: detailContent),
          ],
        ),
      ),
    );
  }
}

class _SourceImagesCard extends StatelessWidget {
  const _SourceImagesCard({required this.records});

  final List<MaterialImageRecord> records;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('原始讲义记录', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
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
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      ClipRRect(
                        borderRadius: BorderRadius.circular(AppRadii.input),
                        child: record.url.isEmpty
                            ? Container(
                                width: 64,
                                height: 64,
                                color: AppColors.paperWhite,
                                child: const Icon(Icons.image_outlined),
                              )
                            : Image.network(
                                record.url,
                                width: 64,
                                height: 64,
                                fit: BoxFit.cover,
                              ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              '第 ${record.pageIndex} 页 · ${record.imageTitle.isEmpty ? record.originalFilename : record.imageTitle}',
                              style: AppTextStyles.cardTitle,
                            ),
                            const SizedBox(height: AppSpacing.xxs),
                            Text(_sourceLabel(record.sourceType),
                                style: AppTextStyles.helper),
                            if (record.vocabulary.isNotEmpty)
                              Text('单词：${record.vocabulary.join('、')}',
                                  style: AppTextStyles.helper),
                            if (record.sentences.isNotEmpty)
                              Text('句子：${record.sentences.join(' / ')}',
                                  style: AppTextStyles.helper),
                            if (record.details.isNotEmpty)
                              Text('细节：${record.details.join('；')}',
                                  style: AppTextStyles.helper),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LearningAssetsCard extends ConsumerWidget {
  const _LearningAssetsCard({
    required this.materialId,
    required this.assets,
  });

  final List<LearningAsset> assets;
  final String materialId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text('核心学习资产', style: AppTextStyles.sectionTitle),
              const SizedBox(width: AppSpacing.sm),
              const StickerBadge(label: '图文音', color: AppColors.mintLeaf),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ...assets.map(
            (asset) => _LearningAssetDetailTile(
              materialId: materialId,
              asset: asset,
            ),
          ),
        ],
      ),
    );
  }
}

class _LearningAssetDetailTile extends ConsumerStatefulWidget {
  const _LearningAssetDetailTile({
    required this.materialId,
    required this.asset,
  });

  final LearningAsset asset;
  final String materialId;

  @override
  ConsumerState<_LearningAssetDetailTile> createState() =>
      _LearningAssetDetailTileState();
}

class _LearningAssetDetailTileState
    extends ConsumerState<_LearningAssetDetailTile> {
  String? _accentError;
  bool _updatingAccent = false;

  Future<void> _updatePrimaryAccent(String selected) async {
    setState(() {
      _accentError = null;
      _updatingAccent = true;
    });
    try {
      await ref.read(appRepositoryProvider).updateLearningAssetPrimaryAccent(
            materialId: widget.materialId,
            assetId: widget.asset.id,
            primaryAccent: selected,
          );
      ref.invalidate(materialProvider(widget.materialId));
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _accentError = describeApiError(error, fallback: '发音切换失败，请稍后重试。');
      });
    } finally {
      if (mounted) {
        setState(() {
          _updatingAccent = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asset = widget.asset;
    final selectedAccent = asset.primaryAccent == 'uk' ? 'uk' : 'us';
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
              _GeneratedAssetImage(asset: asset),
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
                    const SizedBox(height: AppSpacing.xxs),
                    Text(
                      '配图：${_mediaStatusLabel(asset.generatedImageStatus)}',
                      style: AppTextStyles.helper,
                    ),
                    Text(
                      '美式：${_mediaStatusLabel(asset.ttsUsStatus)} · 英式：${_mediaStatusLabel(asset.ttsUkStatus)}',
                      style: AppTextStyles.helper,
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    SegmentedButton<String>(
                      segments: const <ButtonSegment<String>>[
                        ButtonSegment<String>(
                          value: 'us',
                          label: Text('美式'),
                        ),
                        ButtonSegment<String>(
                          value: 'uk',
                          label: Text('英式'),
                        ),
                      ],
                      selected: <String>{selectedAccent},
                      onSelectionChanged: _updatingAccent
                          ? null
                          : (selection) => _updatePrimaryAccent(
                                selection.single,
                              ),
                    ),
                    if (_accentError != null) ...<Widget>[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        _accentError!,
                        style: AppTextStyles.helper
                            .copyWith(color: AppColors.cocoaCoral),
                      ),
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

class _GeneratedAssetImage extends StatelessWidget {
  const _GeneratedAssetImage({required this.asset});

  final LearningAsset asset;

  @override
  Widget build(BuildContext context) {
    if (asset.generatedImageStatus != 'ready' ||
        asset.generatedImageUrl.isEmpty) {
      return _GeneratedImagePlaceholder(status: asset.generatedImageStatus);
    }
    if (asset.generatedImageUrl.toLowerCase().endsWith('.svg')) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadii.input),
        child: SvgPicture.network(
          asset.generatedImageUrl,
          width: 88,
          height: 88,
          fit: BoxFit.cover,
          placeholderBuilder: (context) =>
              _GeneratedImagePlaceholder(status: asset.generatedImageStatus),
          errorBuilder: (context, error, stackTrace) =>
              const _GeneratedImagePlaceholder(status: 'failed'),
        ),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.input),
      child: Image.network(
        asset.generatedImageUrl,
        width: 88,
        height: 88,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) =>
            const _GeneratedImagePlaceholder(status: 'failed'),
      ),
    );
  }
}

class _GeneratedImagePlaceholder extends StatelessWidget {
  const _GeneratedImagePlaceholder({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 88,
      height: 88,
      decoration: BoxDecoration(
        color: AppColors.paperWhite,
        borderRadius: BorderRadius.circular(AppRadii.input),
      ),
      child: Icon(
        status == 'failed'
            ? Icons.error_outline_rounded
            : Icons.hourglass_top_rounded,
        color: AppColors.cocoaCoral,
      ),
    );
  }
}

String _assetKindLabel(String kind) {
  return switch (kind) {
    'sentence' => '句子',
    'phrase' => '短语',
    _ => '单词',
  };
}

String _mediaStatusLabel(String status) {
  return switch (status) {
    'ready' => '已生成',
    'processing' => '生成中',
    'failed' => '失败',
    _ => '等待生成',
  };
}

String _sourceLabel(String sourceType) {
  return sourceType == 'camera' ? '相机拍摄' : '相册选择';
}

Color _lessonAccent(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return AppColors.mintLeaf;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return AppColors.butterYellow;
  }
  return AppColors.skyBlue;
}

IconData _lessonIcon(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return Icons.pets_rounded;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return Icons.looks_one_rounded;
  }
  return Icons.menu_book_rounded;
}
