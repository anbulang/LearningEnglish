import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final appAnalyticsProvider = Provider<AppAnalytics>((ref) => const AppAnalytics());

class AppAnalytics {
  const AppAnalytics();

  void track(String name, [Map<String, Object?> properties = const <String, Object?>{}]) {
    debugPrint('analytics:$name $properties');
  }
}
