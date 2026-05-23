import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../../core/widgets/status_chip.dart';
import '../../profiles/data/demo_data.dart';
import '../data/app_repository.dart';
import 'material_navigation.dart';

class MaterialsLibraryScreen extends ConsumerStatefulWidget {
  const MaterialsLibraryScreen({super.key});

  @override
  ConsumerState<MaterialsLibraryScreen> createState() =>
      _MaterialsLibraryScreenState();
}

class _MaterialsLibraryScreenState
    extends ConsumerState<MaterialsLibraryScreen> {
  final Set<String> _locallyDeletedMaterialIds = <String>{};

  void _hideDeletedMaterial(String materialId) {
    setState(() {
      _locallyDeletedMaterialIds.add(materialId);
    });
  }

  @override
  Widget build(BuildContext context) {
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
            final visibleItems = items
                .where((item) => !_locallyDeletedMaterialIds.contains(item.id))
                .toList();
            if (visibleItems.isEmpty) {
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
            return visibleItems
                .map(
                  (material) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.md),
                    child: Dismissible(
                      key: ValueKey<String>(
                          'material-dismissible-${material.id}'),
                      direction: DismissDirection.endToStart,
                      background: const _DeleteMaterialBackground(),
                      confirmDismiss: (_) => _confirmAndDeleteMaterial(
                        context,
                        ref,
                        material,
                        onDeleted: _hideDeletedMaterial,
                      ),
                      child: AppCard(
                        child: InkWell(
                          key: ValueKey<String>('material-card-${material.id}'),
                          borderRadius: BorderRadius.circular(AppRadii.card),
                          onTap: () =>
                              context.go(materialDestination(material)),
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
                                                style:
                                                    AppTextStyles.cardTitle)),
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

    final visibleMaterials = materials.valueOrNull
        ?.where((item) => !_locallyDeletedMaterialIds.contains(item.id))
        .toList();
    final selected =
        visibleMaterials?.isNotEmpty == true ? visibleMaterials!.first : null;
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
                                  context.go(materialDestination(selected)),
                              child: Text(
                                selected.status == MaterialStatus.ready
                                    ? '查看课程详情'
                                    : '查看 AI 校对',
                              ),
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

class _DeleteMaterialBackground extends StatelessWidget {
  const _DeleteMaterialBackground();

  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      decoration: BoxDecoration(
        color: const Color(0xFFB3261E),
        borderRadius: BorderRadius.circular(AppRadii.card),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: <Widget>[
          Icon(Icons.delete_rounded, color: AppColors.paperWhite),
          SizedBox(width: AppSpacing.xs),
          Text(
            '删除',
            style: TextStyle(
              color: AppColors.paperWhite,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

Future<bool> _confirmAndDeleteMaterial(
  BuildContext context,
  WidgetRef ref,
  CourseMaterial material, {
  required ValueChanged<String> onDeleted,
}) async {
  final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('删除这份课程资料？'),
          content: const Text('删除后课程详情、知识点和复习任务将一起移除。'),
          actions: <Widget>[
            TextButton(
              key: const ValueKey<String>('cancel-delete-material'),
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              key: const ValueKey<String>('confirm-delete-material'),
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('删除'),
            ),
          ],
        ),
      ) ??
      false;

  if (!confirmed || !context.mounted) {
    return false;
  }

  try {
    await ref.read(appRepositoryProvider).deleteMaterial(material.id);
    onDeleted(material.id);
    ref.invalidate(materialsProvider);
    ref.invalidate(reviewTasksProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已删除课程资料')),
      );
    }
    return true;
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('删除失败，请稍后重试。')),
      );
    }
    return false;
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
