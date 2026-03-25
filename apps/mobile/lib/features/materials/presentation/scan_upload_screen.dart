import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/widgets/app_card.dart';

class ScanUploadScreen extends StatelessWidget {
  const ScanUploadScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);

    final preview = AppCard(
      child: AspectRatio(
        aspectRatio: formFactor.isTablet ? 4 / 3 : 3 / 4,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: AppColors.softSheet,
            borderRadius: BorderRadius.circular(AppRadii.card),
          ),
          child: const Center(
            child: Icon(Icons.document_scanner_rounded, size: 64),
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
          const Row(
            children: <Widget>[
              Expanded(child: Chip(label: Text('自动裁边 已开启'))),
              SizedBox(width: AppSpacing.xs),
              Expanded(child: Chip(label: Text('清晰度增强 已开启'))),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton.icon(
                onPressed: () => context.go('/materials/review'),
                icon: const Icon(Icons.cloud_upload_rounded),
                label: const Text('完成上传'),
              ),
              OutlinedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.add_photo_alternate_outlined),
                label: const Text('继续加页'),
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
