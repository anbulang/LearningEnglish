import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/state_panel.dart';
import '../data/scan_draft_controller.dart';

class ScanUploadScreen extends ConsumerWidget {
  const ScanUploadScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final formFactor = formFactorOf(context);
    final draft = ref.watch(scanDraftProvider);

    final preview = AppCard(
      child: draft.pages.isEmpty
          ? StatePanel(
              title: '还没有扫描页',
              description: '先拍一页讲义，再继续上传和识别。',
              action: FilledButton(
                onPressed: ref.read(scanDraftProvider.notifier).addPage,
                child: const Text('添加第一页'),
              ),
            )
          : AspectRatio(
              aspectRatio: formFactor.isTablet ? 4 / 3 : 3 / 4,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: AppColors.softSheet,
                  borderRadius: BorderRadius.circular(AppRadii.card),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    const Icon(Icons.document_scanner_rounded, size: 64),
                    const SizedBox(height: AppSpacing.sm),
                    Text('已暂存 ${draft.pages.length} 页'),
                  ],
                ),
              ),
            ),
    );

    final controls = AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('拍照上传', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          const Text('支持多页扫描、自动增强和 PDF 合成。'),
          const SizedBox(height: AppSpacing.md),
          SwitchListTile(
            value: draft.autoEnhance,
            contentPadding: EdgeInsets.zero,
            title: const Text('自动增强'),
            subtitle: const Text('保持清晰度与裁边效果'),
            onChanged: ref.read(scanDraftProvider.notifier).toggleEnhance,
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: draft.pages
                .map((page) => Chip(label: Text(page)))
                .toList(),
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton.icon(
                onPressed: () {
                  ref.read(appAnalyticsProvider).track('material_upload_submitted', {
                    'pages': draft.pages.length,
                    'autoEnhance': draft.autoEnhance,
                  });
                  context.go('/materials/review');
                },
                icon: const Icon(Icons.cloud_upload_rounded),
                label: const Text('完成上传'),
              ),
              OutlinedButton.icon(
                onPressed: ref.read(scanDraftProvider.notifier).addPage,
                icon: const Icon(Icons.add_photo_alternate_outlined),
                label: const Text('继续加页'),
              ),
              TextButton.icon(
                onPressed: ref.read(scanDraftProvider.notifier).clear,
                icon: const Icon(Icons.delete_outline_rounded),
                label: const Text('清空草稿'),
              ),
            ],
          ),
        ],
      ),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('上传讲义')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: formFactor.isTablet
            ? Row(
                children: <Widget>[
                  Expanded(child: preview),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(child: controls),
                ],
              )
            : Column(
                children: <Widget>[
                  preview,
                  const SizedBox(height: AppSpacing.md),
                  controls,
                ],
              ),
      ),
    );
  }
}
