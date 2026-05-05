import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/assets/app_illustrations.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/illustrated_surface.dart';
import '../../../core/widgets/state_panel.dart';
import '../../profiles/data/demo_data.dart';
import '../data/app_repository.dart';
import '../data/scan_draft_controller.dart';

class ScanUploadScreen extends ConsumerStatefulWidget {
  const ScanUploadScreen({super.key});

  @override
  ConsumerState<ScanUploadScreen> createState() => _ScanUploadScreenState();
}

class _ScanUploadScreenState extends ConsumerState<ScanUploadScreen> {
  final ImagePicker _picker = ImagePicker();
  bool _submitting = false;
  String? _errorMessage;

  Future<void> _pickPage() async {
    final image =
        await _picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (image == null) {
      return;
    }
    final draft = ref.read(scanDraftProvider);
    ref
        .read(scanDraftProvider.notifier)
        .setPages(<XFile>[...draft.pages, image]);
  }

  Future<void> _takePhoto() async {
    final image =
        await _picker.pickImage(source: ImageSource.camera, imageQuality: 90);
    if (image == null) {
      return;
    }
    final draft = ref.read(scanDraftProvider);
    ref
        .read(scanDraftProvider.notifier)
        .setPages(<XFile>[...draft.pages, image]);
  }

  Future<void> _submit() async {
    final child = ref.read(activeChildProvider);
    final draft = ref.read(scanDraftProvider);
    if (child == null || draft.pages.isEmpty) {
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      final created = await ref.read(appRepositoryProvider).uploadMaterial(
            childId: child.id,
            teacherName: draft.teacherName,
            lessonDate: draft.lessonDate,
            title: draft.title,
            topic: draft.topic,
            files: draft.pages,
          );
      ref
          .read(appAnalyticsProvider)
          .track('material_upload_submitted', <String, Object?>{
        'pages': draft.pages.length,
        'autoEnhance': draft.autoEnhance,
        'materialId': created.material.id,
      });
      ref.invalidate(materialsProvider);
      ref.read(scanDraftProvider.notifier).clear();
      if (!mounted) {
        return;
      }
      context.go(
          '/materials/review/${created.job.id}?materialId=${created.material.id}');
    } catch (error) {
      setState(() {
        _errorMessage = describeApiError(error, fallback: '上传失败，请稍后重试。');
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
    final formFactor = formFactorOf(context);
    final draft = ref.watch(scanDraftProvider);

    final preview = AppCard(
      child: draft.pages.isEmpty
          ? StatePanel(
              title: '还没有扫描页',
              description: '直接拍照，或从相册选择已经拍好的讲义页。',
              assetPath: AppIllustrations.stateEmpty,
              action: Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: <Widget>[
                  FilledButton.icon(
                    onPressed: _takePhoto,
                    icon: const Icon(Icons.camera_alt_rounded),
                    label: const Text('拍照'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _pickPage,
                    icon: const Icon(Icons.photo_library_outlined),
                    label: const Text('从相册选择'),
                  ),
                ],
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
                    const Icon(Icons.document_scanner_rounded,
                        size: 64, color: AppColors.cocoaCoral),
                    const SizedBox(height: AppSpacing.sm),
                    Text('已选择 ${draft.pages.length} 页讲义'),
                    const SizedBox(height: AppSpacing.xs),
                    Text(draft.pages.map((item) => item.name).join('\n'),
                        textAlign: TextAlign.center),
                  ],
                ),
              ),
            ),
    );

    final controls = AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: const <Widget>[
              Text('拍照上传', style: AppTextStyles.sectionTitle),
              SizedBox(width: AppSpacing.sm),
              StickerBadge(label: '讲义变复习包', icon: Icons.auto_awesome_rounded),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          const Text('拍下讲义后直接开始识别。课程标题、主题、词汇和句型会由 AI 先整理，再交给你校对。'),
          if (_errorMessage != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            StatePanel(
              title: '上传失败',
              description: _errorMessage!,
              icon: Icons.error_outline_rounded,
              assetPath: AppIllustrations.stateError,
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton.icon(
                onPressed: _submitting || draft.pages.isEmpty ? null : _submit,
                icon: const Icon(Icons.auto_awesome_rounded),
                label: Text(_submitting ? '识别中...' : '开始识别'),
              ),
              OutlinedButton.icon(
                onPressed: _submitting ? null : _takePhoto,
                icon: const Icon(Icons.camera_alt_rounded),
                label: const Text('拍照'),
              ),
              OutlinedButton.icon(
                onPressed: _submitting ? null : _pickPage,
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('从相册选择'),
              ),
              TextButton.icon(
                onPressed: _submitting
                    ? null
                    : ref.read(scanDraftProvider.notifier).clear,
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
                  Expanded(
                    child: ListView(
                      children: const <Widget>[
                        IllustratedHeroCard(
                          eyebrow: '上传讲义',
                          title: '拍一拍课堂讲义，下一步就能生成孩子的复习包',
                          description:
                              '上传页现在更像一个温和的扫描工作台，先整理讲义，再交给 AI 识别和家长校对。',
                          accent: AppColors.skyBlue,
                          illustration: Icons.camera_alt_rounded,
                          assetPath: AppIllustrations.heroUpload,
                          badge: StickerBadge(
                              label: '多页支持',
                              icon: Icons.layers_rounded,
                              color: AppColors.butterYellow),
                        ),
                        SizedBox(height: AppSpacing.md),
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(child: preview),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(child: controls),
                ],
              )
            : ListView(
                children: <Widget>[
                  const IllustratedHeroCard(
                    eyebrow: '上传讲义',
                    title: '把课堂纸张拍下来，交给 AI 帮你整理复习包',
                    description: '先选讲义页，再补课程标题和老师名，最后一键上传进入校对流程。',
                    accent: AppColors.skyBlue,
                    illustration: Icons.camera_alt_rounded,
                    assetPath: AppIllustrations.heroUpload,
                    badge: StickerBadge(
                        label: '轻松整理', icon: Icons.auto_awesome_rounded),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  preview,
                  const SizedBox(height: AppSpacing.md),
                  controls,
                ],
              ),
      ),
    );
  }
}
