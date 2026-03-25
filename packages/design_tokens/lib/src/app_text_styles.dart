import 'package:flutter/material.dart';

import 'app_colors.dart';

abstract final class AppTextStyles {
  static const String displayFamily = 'Plus Jakarta Sans';
  static const String bodyFamily = 'Be Vietnam Pro';

  static const TextStyle pageTitle = TextStyle(
    fontFamily: displayFamily,
    fontSize: 28,
    height: 32 / 28,
    fontWeight: FontWeight.w600,
    color: AppColors.inkCocoa,
  );

  static const TextStyle sectionTitle = TextStyle(
    fontFamily: displayFamily,
    fontSize: 20,
    height: 24 / 20,
    fontWeight: FontWeight.w600,
    color: AppColors.inkCocoa,
  );

  static const TextStyle cardTitle = TextStyle(
    fontFamily: displayFamily,
    fontSize: 16,
    height: 20 / 16,
    fontWeight: FontWeight.w600,
    color: AppColors.inkCocoa,
  );

  static const TextStyle body = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 14,
    height: 20 / 14,
    fontWeight: FontWeight.w400,
    color: AppColors.dustBrown,
  );

  static const TextStyle helper = TextStyle(
    fontFamily: bodyFamily,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w500,
    color: AppColors.dustBrown,
  );
}
