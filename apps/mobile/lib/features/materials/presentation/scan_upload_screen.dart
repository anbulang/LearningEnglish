import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/network/api_error.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/no_child_state_panel.dart';
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
    ref.read(scanDraftProvider.notifier).setPages(<ScanDraftPage>[
      ...draft.pages,
      ScanDraftPage(file: image, sourceType: 'gallery'),
    ]);
  }

  Future<void> _takePhoto() async {
    final image =
        await _picker.pickImage(source: ImageSource.camera, imageQuality: 90);
    if (image == null) {
      return;
    }
    final draft = ref.read(scanDraftProvider);
    ref.read(scanDraftProvider.notifier).setPages(<ScanDraftPage>[
      ...draft.pages,
      ScanDraftPage(file: image, sourceType: 'camera'),
    ]);
  }

  Future<void> _submit() async {
    final child = ref.read(activeChildProvider);
    final draft = ref.read(scanDraftProvider);
    if (child == null) {
      setState(() => _errorMessage = '请先添加孩子档案，再上传讲义。');
      return;
    }
    if (draft.pages.isEmpty) {
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
    final hasPages = draft.pages.isNotEmpty;
    final hasChild = ref.watch(activeChildProvider) != null;

    if (!hasChild) {
      return Scaffold(
        appBar: AppBar(title: const Text('上传讲义'), centerTitle: false),
        body: const Padding(
          padding: EdgeInsets.all(AppSpacing.md),
          child: NoChildStatePanel(description: '上传讲义前，请先为孩子建立档案。'),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('上传讲义'),
        centerTitle: false,
      ),
      body: SafeArea(
        bottom: false,
        child: ListView(
          padding: EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.sm,
            AppSpacing.md,
            formFactor.isTablet ? AppSpacing.xl : 132,
          ),
          children: <Widget>[
            const _UploadHeader(),
            const SizedBox(height: AppSpacing.md),
            if (hasPages)
              _SelectedPagesPanel(
                pages: draft.pages,
                isSubmitting: _submitting,
                onTakePhoto: _takePhoto,
                onPickPage: _pickPage,
                onClear: ref.read(scanDraftProvider.notifier).clear,
              )
            else
              _EmptyUploadPanel(
                onTakePhoto: _takePhoto,
                onPickPage: _pickPage,
              ),
            if (_errorMessage != null) ...<Widget>[
              const SizedBox(height: AppSpacing.md),
              _InlineError(message: _errorMessage!),
            ],
            const SizedBox(height: AppSpacing.md),
            const _RecognitionSummary(),
          ],
        ),
      ),
      bottomNavigationBar: _RecognitionActionBar(
        pageCount: draft.pages.length,
        isSubmitting: _submitting,
        onSubmit: _submit,
      ),
    );
  }
}

class _UploadHeader extends StatelessWidget {
  const _UploadHeader();

  @override
  Widget build(BuildContext context) {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text('拍讲义，生成复习包', style: AppTextStyles.pageTitle),
        SizedBox(height: AppSpacing.xs),
        Text(
          '把英语讲义拍下来，AI 会先整理标题、主题、词汇和句型，再交给你校对。',
          style: AppTextStyles.body,
        ),
      ],
    );
  }
}

class _EmptyUploadPanel extends StatelessWidget {
  const _EmptyUploadPanel({
    required this.onTakePhoto,
    required this.onPickPage,
  });

  final VoidCallback onPickPage;
  final VoidCallback onTakePhoto;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.softSheet.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(AppRadii.card),
          border: Border.all(
            color: AppColors.coralJam.withValues(alpha: 0.35),
            width: 1.5,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            children: <Widget>[
              const _ScanIcon(),
              const SizedBox(height: AppSpacing.md),
              const Text('添加讲义页', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.xs),
              const Text(
                '拍摄纸质讲义，或选择已经拍好的图片。',
                textAlign: TextAlign.center,
                style: AppTextStyles.body,
              ),
              const SizedBox(height: AppSpacing.lg),
              Row(
                children: <Widget>[
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: onTakePhoto,
                      icon: const Icon(Icons.camera_alt_rounded),
                      label: const Text('拍照'),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onPickPage,
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('从相册选择'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectedPagesPanel extends StatelessWidget {
  const _SelectedPagesPanel({
    required this.pages,
    required this.isSubmitting,
    required this.onTakePhoto,
    required this.onPickPage,
    required this.onClear,
  });

  final bool isSubmitting;
  final VoidCallback onClear;
  final VoidCallback onPickPage;
  final VoidCallback onTakePhoto;
  final List<ScanDraftPage> pages;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const _SmallScanIcon(),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('已添加 ${pages.length} 页',
                        style: AppTextStyles.sectionTitle),
                    const SizedBox(height: AppSpacing.xxs),
                    const Text('确认页数后开始识别。', style: AppTextStyles.helper),
                  ],
                ),
              ),
              IconButton(
                onPressed: isSubmitting ? null : onClear,
                tooltip: '清空草稿',
                icon: const Icon(Icons.delete_outline_rounded),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          ...pages.asMap().entries.map(
                (entry) => _PageListItem(
                  index: entry.key + 1,
                  page: entry.value,
                ),
              ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: isSubmitting ? null : onTakePhoto,
                  icon: const Icon(Icons.camera_alt_rounded),
                  label: const Text('继续拍照'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: isSubmitting ? null : onPickPage,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('继续选择'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PageListItem extends StatelessWidget {
  const _PageListItem({
    required this.index,
    required this.page,
  });

  final int index;
  final ScanDraftPage page;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.softSheet.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(AppRadii.input),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            children: <Widget>[
              CircleAvatar(
                radius: 16,
                backgroundColor: AppColors.paperWhite,
                child: Text('$index', style: AppTextStyles.helper),
              ),
              const SizedBox(width: AppSpacing.sm),
              _PageThumbnail(page: page),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      '第 $index 页',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTextStyles.cardTitle,
                    ),
                    const SizedBox(height: AppSpacing.xxs),
                    Text(page.sourceLabel, style: AppTextStyles.helper),
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

class _PageThumbnail extends StatefulWidget {
  const _PageThumbnail({required this.page});

  final ScanDraftPage page;

  @override
  State<_PageThumbnail> createState() => _PageThumbnailState();
}

class _PageThumbnailState extends State<_PageThumbnail> {
  late Future<Uint8List> _bytesFuture;

  @override
  void initState() {
    super.initState();
    _bytesFuture = widget.page.file.readAsBytes();
  }

  @override
  void didUpdateWidget(covariant _PageThumbnail oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.page.file.path != widget.page.file.path) {
      _bytesFuture = widget.page.file.readAsBytes();
    }
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.input),
      child: SizedBox(
        width: 72,
        height: 88,
        child: FutureBuilder<Uint8List>(
          future: _bytesFuture,
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return _ThumbnailPlaceholder(icon: Icons.image_outlined);
            }
            return Image.memory(
              snapshot.data!,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) =>
                  const _ThumbnailPlaceholder(
                icon: Icons.image_not_supported_outlined,
              ),
            );
          },
        ),
      ),
    );
  }
}

class _ThumbnailPlaceholder extends StatelessWidget {
  const _ThumbnailPlaceholder({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.paperWhite,
      alignment: Alignment.center,
      child: Icon(icon, color: AppColors.cocoaCoral),
    );
  }
}

class _RecognitionSummary extends StatelessWidget {
  const _RecognitionSummary();

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.butterYellow.withValues(alpha: 0.65),
              borderRadius: BorderRadius.circular(AppRadii.input),
            ),
            child: const Icon(Icons.auto_awesome_rounded,
                color: AppColors.inkCocoa, size: 20),
          ),
          const SizedBox(width: AppSpacing.sm),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('识别后进入校对', style: AppTextStyles.cardTitle),
                SizedBox(height: AppSpacing.xxs),
                Text('AI 草稿会先进入校对页，不会直接生成最终课程。', style: AppTextStyles.helper),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.errorSurface,
        borderRadius: BorderRadius.circular(AppRadii.card),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Icon(Icons.error_outline_rounded,
                color: AppColors.cocoaCoral),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: Text(message, style: AppTextStyles.body)),
          ],
        ),
      ),
    );
  }
}

class _RecognitionActionBar extends StatelessWidget {
  const _RecognitionActionBar({
    required this.pageCount,
    required this.isSubmitting,
    required this.onSubmit,
  });

  final bool isSubmitting;
  final VoidCallback onSubmit;
  final int pageCount;

  @override
  Widget build(BuildContext context) {
    final canSubmit = pageCount > 0 && !isSubmitting;
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          AppSpacing.sm,
          AppSpacing.md,
          AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: AppColors.paperWhite,
          border: Border(
            top: BorderSide(
                color: AppColors.outlineVariant.withValues(alpha: 0.45)),
          ),
        ),
        child: FilledButton.icon(
          onPressed: canSubmit ? onSubmit : null,
          icon: Icon(isSubmitting
              ? Icons.hourglass_top_rounded
              : Icons.auto_awesome_rounded),
          label: Text(
            isSubmitting
                ? '识别中...'
                : pageCount == 0
                    ? '先添加讲义页'
                    : '开始识别',
          ),
        ),
      ),
    );
  }
}

class _ScanIcon extends StatelessWidget {
  const _ScanIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 88,
      height: 88,
      decoration: BoxDecoration(
        color: AppColors.paperWhite,
        borderRadius: BorderRadius.circular(AppRadii.panel),
      ),
      child: const Icon(Icons.document_scanner_rounded,
          color: AppColors.cocoaCoral, size: 44),
    );
  }
}

class _SmallScanIcon extends StatelessWidget {
  const _SmallScanIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: AppColors.softSheet,
        borderRadius: BorderRadius.circular(AppRadii.input),
      ),
      child: const Icon(Icons.document_scanner_rounded,
          color: AppColors.cocoaCoral, size: 24),
    );
  }
}
