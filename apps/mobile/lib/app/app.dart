import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/app_theme.dart';
import '../features/profiles/data/demo_data.dart';
import 'routing/app_router.dart';

class LearningEnglishApp extends ConsumerStatefulWidget {
  const LearningEnglishApp({super.key});

  @override
  ConsumerState<LearningEnglishApp> createState() => _LearningEnglishAppState();
}

class _LearningEnglishAppState extends ConsumerState<LearningEnglishApp>
    with WidgetsBindingObserver {
  DateTime? _lastWeekStart;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _lastWeekStart = _currentWeekStart();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      return;
    }
    final now = _currentWeekStart();
    if (_lastWeekStart != now) {
      _lastWeekStart = now;
      // The ISO week rolled over while the app was backgrounded. weeklyReport /
      // weeklyTrends are non-auto-dispose caches keyed only by child, so without
      // this they'd keep serving last week's snapshot (mislabeled 本周) until some
      // unrelated action invalidates them. Drop them on the rollover.
      ref.invalidate(weeklyReportProvider);
      ref.invalidate(weeklyTrendsProvider);
    }
  }

  /// Monday of the current ISO week in the product timezone (UTC+8, matching the
  /// backend's `PRODUCT_TZ`), as a date-only value.
  DateTime _currentWeekStart() {
    final local = DateTime.now().toUtc().add(const Duration(hours: 8));
    final dateOnly = DateTime.utc(local.year, local.month, local.day);
    return dateOnly.subtract(Duration(days: dateOnly.weekday - 1));
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'LearningEnglish',
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      theme: AppTheme.light(),
    );
  }
}
