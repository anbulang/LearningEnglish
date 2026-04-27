import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../../core/widgets/status_chip.dart';
import '../../profiles/data/demo_data.dart';

class MaterialsLibraryScreen extends ConsumerWidget {
  const MaterialsLibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final materials = ref.watch(materialsProvider);
    final formFactor = formFactorOf(context);

    final list = Column(
      children: <Widget>[
        IllustratedHeroCard(
          eyebrow: '资料整理',
          title: '把每一张课堂讲义都整理成能复习的小课包',
          description: '先搜主题，再按状态筛选。每一课都带上更清楚的主题缩略图和复习状态。',
          accent: AppColors.skyBlue,
          illustration: Icons.collections_bookmark_rounded,
          assetPath: AppIllustrations.heroUpload,
          badge: const StickerBadge(
              label: '讲义宝', icon: Icons.auto_awesome_rounded),
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          decoration: InputDecoration(
            hintText: '搜索单词、主题、日期',
            prefixIcon: const Icon(Icons.search_rounded),
            suffixIcon: IconButton(
              onPressed: () {},
              icon: const Icon(Icons.tune_rounded),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: const <Widget>[
            StickerBadge(label: '全部'),
            StickerBadge(label: '待校对', color: AppColors.errorSurface),
            StickerBadge(label: '可复习', color: AppColors.mintLeaf),
            StickerBadge(label: '动物', color: AppColors.skyBlue),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        ...materials.when(
          data: (items) {
            if (items.isEmpty) {
              return <Widget>[
                StatePanel(
                  title: '还没有课程资料',
                  description: '上传第一份讲义后，这里会自动整理成课程卡片。',
                  assetPath: AppIllustrations.stateEmpty,
                  action: FilledButton(
                    onPressed: () => context.go('/materials/scan'),
                    child: const Text('上传第一份讲义'),
                  ),
                ),
              ];
            }
            return items
                .map(
                  (material) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.md),
                    child: AppCard(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(AppRadii.card),
                        onTap: () => context.go('/lessons/${material.id}'),
                        child: Row(
                          children: <Widget>[
                            LessonCoverThumbnail(
                              title: material.title,
                              subtitle: material.topic,
                              icon: _libraryIcon(material.topic),
                              accent: _libraryAccent(material.topic),
                              assetPath:
                                  AppIllustrations.topicFor(material.topic),
                            ),
                            const SizedBox(width: AppSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Row(
                                    children: <Widget>[
                                      Expanded(
                                          child: Text(material.title,
                                              style: AppTextStyles.cardTitle)),
                                      MaterialStatusChip(material.status),
                                    ],
                                  ),
                                  const SizedBox(height: AppSpacing.xs),
                                  Text(
                                    '${material.lessonDate.month}/${material.lessonDate.day} · ${material.teacherName}',
                                  ),
                                  const SizedBox(height: AppSpacing.xs),
                                  Text('主题：${material.topic}',
                                      style: AppTextStyles.helper),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                )
                .toList();
          },
          loading: () => const <Widget>[
            Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
              child: Center(child: CircularProgressIndicator()),
            ),
          ],
          error: (_, __) => <Widget>[
            StatePanel(
              title: '资料库加载失败',
              description: '请检查网络或稍后重试。',
              assetPath: AppIllustrations.stateNetwork,
              action: FilledButton(
                onPressed: () => ref.invalidate(materialsProvider),
                child: const Text('重新加载'),
              ),
            ),
          ],
        ),
      ],
    );

    if (!formFactor.isTablet) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('资料库'),
          actions: <Widget>[
            IconButton(
              onPressed: () => context.go('/materials/scan'),
              icon: const Icon(Icons.add_a_photo_rounded),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: <Widget>[list],
        ),
      );
    }

    final selected = materials.valueOrNull?.isNotEmpty == true
        ? materials.valueOrNull!.first
        : null;
    return Scaffold(
      appBar: AppBar(
        title: const Text('资料库'),
        actions: <Widget>[
          FilledButton.icon(
            onPressed: () => context.go('/materials/scan'),
            icon: const Icon(Icons.add_a_photo_rounded),
            label: const Text('上传讲义'),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(child: ListView(children: <Widget>[list])),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: selected == null
                  ? const StatePanel(
                      title: '选择一份课程资料',
                      description: '平板模式下会在右侧显示讲义摘要和详情入口。',
                      assetPath: AppIllustrations.stateEmpty,
                    )
                  : AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          IllustratedHeroCard(
                            eyebrow: '课程预览',
                            title: selected.title,
                            description: '右侧保留摘要与 OCR 内容，帮助你在平板上更快决定先复习哪一课。',
                            accent: _libraryAccent(selected.topic),
                            illustration: _libraryIcon(selected.topic),
                            assetPath:
                                AppIllustrations.topicFor(selected.topic),
                            badge: StickerBadge(
                                label: selected.topic,
                                color: _libraryAccent(selected.topic)),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          const Text('OCR 摘要'),
                          const SizedBox(height: AppSpacing.xs),
                          Text(selected.ocrText),
                          const Spacer(),
                          Align(
                            alignment: Alignment.bottomLeft,
                            child: FilledButton(
                              onPressed: () =>
                                  context.go('/lessons/${selected.id}'),
                              child: const Text('查看课程详情'),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

Color _libraryAccent(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return AppColors.mintLeaf;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return AppColors.butterYellow;
  }
  if (topic.contains('自然拼读') || topic.toLowerCase().contains('phonics')) {
    return AppColors.skyBlue;
  }
  return AppColors.softSheet;
}

IconData _libraryIcon(String topic) {
  if (topic.contains('动物') || topic.toLowerCase().contains('zoo')) {
    return Icons.pets_rounded;
  }
  if (topic.contains('数字') || topic.toLowerCase().contains('count')) {
    return Icons.pin_rounded;
  }
  if (topic.contains('自然拼读') || topic.toLowerCase().contains('phonics')) {
    return Icons.record_voice_over_rounded;
  }
  return Icons.menu_book_rounded;
}
