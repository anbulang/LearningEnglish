import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';
import '../../profiles/data/demo_data.dart';

class MaterialReviewScreen extends ConsumerWidget {
  const MaterialReviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final job = ref.watch(materialJobProvider);
    final formFactor = formFactorOf(context);

    final extracted = AppCard(
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
            onPressed: () => context.go('/lessons/material_demo_1'),
            child: const Text('确认并生成课程详情'),
          ),
        ],
      ),
    );

    if (!formFactor.isTablet) {
      return Scaffold(appBar: AppBar(title: const Text('AI 校对')), body: ListView(padding: const EdgeInsets.all(AppSpacing.md), children: <Widget>[extracted]));
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
