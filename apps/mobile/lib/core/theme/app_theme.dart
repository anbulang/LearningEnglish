import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

class AppTheme {
  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AppColors.coralJam,
      brightness: Brightness.light,
    ).copyWith(
      primary: AppColors.coralJam,
      secondary: AppColors.mintLeaf,
      onPrimary: Colors.white,
      surface: AppColors.paperWhite,
      onSurface: AppColors.inkCocoa,
      outlineVariant: AppColors.outlineVariant,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.warmLinen,
      cardColor: AppColors.paperWhite,
      textTheme: const TextTheme(
        headlineMedium: AppTextStyles.pageTitle,
        titleLarge: AppTextStyles.sectionTitle,
        titleMedium: AppTextStyles.cardTitle,
        bodyMedium: AppTextStyles.body,
        bodySmall: AppTextStyles.helper,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.warmLinen,
        foregroundColor: AppColors.inkCocoa,
        elevation: 0,
        centerTitle: false,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.paperWhite,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.input),
          borderSide: const BorderSide(color: AppColors.outlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.input),
          borderSide: const BorderSide(color: AppColors.outlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.input),
          borderSide: const BorderSide(color: AppColors.coralJam, width: 1.5),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.coralJam,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.softSheet,
        side: const BorderSide(color: AppColors.outlineVariant),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.pill),
        ),
      ),
    );
  }
}
