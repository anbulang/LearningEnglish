import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

import '../../materials/data/app_repository.dart';
import '../../profiles/data/demo_data.dart';

/// Unit list for the active child. Returns null when no child is selected so the
/// UI can show the shared [NoChildStatePanel] instead of an error.
final phonicsUnitsProvider =
    FutureProvider.autoDispose<PhonicsUnitListResponse?>((ref) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    return null;
  }
  return ref.watch(appRepositoryProvider).getPhonicsUnits(child.id);
});

/// One resolved lesson (unit shell + sound cards + words + steps + progress).
/// A missing unit surfaces as a 404 DioException that the screen maps to a
/// friendly empty state via [isNotFoundApiError].
final phonicsUnitProvider = FutureProvider.autoDispose
    .family<PhonicsUnitDetailResponse, String>((ref, unitId) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    throw StateError('No active child selected');
  }
  return ref.watch(appRepositoryProvider).getPhonicsUnit(unitId, child.id);
});

/// Full mastery snapshot for the active child. Returns null when no child is
/// selected. Used by the completion stage to show fresh progress + next unit.
final phonicsProgressProvider =
    FutureProvider.autoDispose<PhonicsProgressResponse?>((ref) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    return null;
  }
  return ref.watch(appRepositoryProvider).getPhonicsProgress(child.id);
});
