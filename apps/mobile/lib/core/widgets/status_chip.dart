import 'package:flutter/material.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

class MaterialStatusChip extends StatelessWidget {
  const MaterialStatusChip(this.status, {super.key});

  final MaterialStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      MaterialStatus.uploaded => ('已上传', AppColors.softSheet),
      MaterialStatus.processing => ('处理中', AppColors.warningSurface),
      MaterialStatus.needsReview => ('待校对', AppColors.errorSurface),
      MaterialStatus.ready => ('可复习', AppColors.successSurface),
      MaterialStatus.failed => ('识别失败', AppColors.errorSurface),
      MaterialStatus.archived => ('已归档', AppColors.softSheet),
    };

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(AppRadii.pill),
      ),
      child: Text(label, style: AppTextStyles.helper),
    );
  }
}
