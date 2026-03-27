import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
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
          children: const <Widget>[
            Chip(label: Text('全部')),
            Chip(label: Text('待校对')),
            Chip(label: Text('可复习')),
            Chip(label: Text('动物')),
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
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(material.title, style: AppTextStyles.cardTitle),
                        subtitle: Padding(
                          padding: const EdgeInsets.only(top: AppSpacing.xs),
                          child: Text('${material.lessonDate.month}/${material.lessonDate.day} · ${material.teacherName}'),
                        ),
                        trailing: MaterialStatusChip(material.status),
                        onTap: () => context.go('/lessons/${material.id}'),
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

    final selected = materials.valueOrNull?.isNotEmpty == true ? materials.valueOrNull!.first : null;
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
                    )
                  : AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(selected.title, style: AppTextStyles.sectionTitle),
                          const SizedBox(height: AppSpacing.sm),
                          Text('主题：${selected.topic}'),
                          const SizedBox(height: AppSpacing.sm),
                          const Text('OCR 摘要'),
                          const SizedBox(height: AppSpacing.xs),
                          Text(selected.ocrText),
                          const Spacer(),
                          Align(
                            alignment: Alignment.bottomLeft,
                            child: FilledButton(
                              onPressed: () => context.go('/lessons/${selected.id}'),
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
