import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../app/responsive/adaptive_layout.dart';
import '../../../core/analytics/app_analytics.dart';
import '../../../core/widgets/app_card.dart';
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
    final image = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (image == null) {
      return;
    }
    final draft = ref.read(scanDraftProvider);
    ref.read(scanDraftProvider.notifier).setPages(<XFile>[...draft.pages, image]);
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
      ref.read(appAnalyticsProvider).track('material_upload_submitted', <String, Object?>{
        'pages': draft.pages.length,
        'autoEnhance': draft.autoEnhance,
        'materialId': created.material.id,
      });
      ref.invalidate(materialsProvider);
      ref.read(scanDraftProvider.notifier).clear();
      if (!mounted) {
        return;
      }
      context.go('/materials/review/${created.job.id}?materialId=${created.material.id}');
    } catch (error) {
      setState(() {
        _errorMessage = error.toString();
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
              description: '先从相册或拍照添加一页讲义，再继续上传。',
              action: FilledButton(
                onPressed: _pickPage,
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
                    Text('已选择 ${draft.pages.length} 页讲义'),
                    const SizedBox(height: AppSpacing.xs),
                    Text(draft.pages.map((item) => item.name).join('\n'), textAlign: TextAlign.center),
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
          const Text('本阶段先接真实图片上传、AI 识别和家长校对链路。'),
          const SizedBox(height: AppSpacing.md),
          TextFormField(
            initialValue: draft.title,
            onChanged: ref.read(scanDraftProvider.notifier).setTitle,
            decoration: const InputDecoration(labelText: '课程标题'),
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            initialValue: draft.teacherName,
            onChanged: ref.read(scanDraftProvider.notifier).setTeacherName,
            decoration: const InputDecoration(labelText: '老师名'),
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            initialValue: draft.topic,
            onChanged: ref.read(scanDraftProvider.notifier).setTopic,
            decoration: const InputDecoration(labelText: '主题'),
          ),
          const SizedBox(height: AppSpacing.md),
          SwitchListTile(
            value: draft.autoEnhance,
            contentPadding: EdgeInsets.zero,
            title: const Text('自动增强'),
            subtitle: const Text('保持清晰度与裁边效果'),
            onChanged: ref.read(scanDraftProvider.notifier).toggleEnhance,
          ),
          if (_errorMessage != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            StatePanel(
              title: '上传失败',
              description: _errorMessage!,
              icon: Icons.error_outline_rounded,
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: <Widget>[
              FilledButton.icon(
                onPressed: _submitting ? null : _submit,
                icon: const Icon(Icons.cloud_upload_rounded),
                label: Text(_submitting ? '上传中...' : '完成上传'),
              ),
              OutlinedButton.icon(
                onPressed: _submitting ? null : _pickPage,
                icon: const Icon(Icons.add_photo_alternate_outlined),
                label: const Text('继续加页'),
              ),
              TextButton.icon(
                onPressed: _submitting ? null : ref.read(scanDraftProvider.notifier).clear,
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
