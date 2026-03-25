import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
import '../../profiles/data/demo_data.dart';

class LessonDetailScreen extends ConsumerWidget {
  const LessonDetailScreen({
    required this.materialId,
    super.key,
  });

  final String materialId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final materials = ref.watch(materialsProvider);
    final material = materials.firstWhere((item) => item.id == materialId);
    final knowledge = ref.watch(knowledgePackProvider);
    final formFactor = formFactorOf(context);

    final detailContent = ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: <Widget>[
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(material.title, style: AppTextStyles.pageTitle),
              const SizedBox(height: AppSpacing.sm),
              Text('${material.teacherName} · ${material.lessonDate.month}/${material.lessonDate.day} · ${material.topic}'),
              const SizedBox(height: AppSpacing.md),
              Text(knowledge.lessonSummary),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('核心单词', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: knowledge.vocabularyItems
                    .map((item) => Chip(label: Text('${item.word} · ${item.meaningCn}')))
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
              Text('重点句型', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.sm),
              ...knowledge.sentencePatterns.map(
                (item) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(item.sentence),
                  subtitle: Text(item.meaningCn),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              FilledButton.icon(
                onPressed: () => context.go('/review/session/$materialId'),
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('开始本课复习'),
              ),
              const SizedBox(height: AppSpacing.sm),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: <Widget>[
                  OutlinedButton.icon(
                    onPressed: () => context.go('/review/speaking/$materialId'),
                    icon: const Icon(Icons.mic_none_rounded),
                    label: const Text('口语陪练'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => context.go('/review/coaching/$materialId'),
                    icon: const Icon(Icons.favorite_border_rounded),
                    label: const Text('亲子陪练'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );

    if (!formFactor.isTablet) {
      return Scaffold(appBar: AppBar(title: const Text('课程详情')), body: detailContent);
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
                        child: const Center(child: Text('Worksheet / PDF Preview')),
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
