import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
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
      error: (error, _) => StatePanel(
        title: '课程详情加载失败',
        description: describeApiError(error, fallback: '课程详情加载失败，请稍后重试。'),
        assetPath: AppIllustrations.stateError,
        action: FilledButton(
          onPressed: () => ref.invalidate(materialProvider(materialId)),
          child: const Text('重新加载'),
        ),
      ),
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
