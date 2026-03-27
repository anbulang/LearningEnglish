import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

import '../../materials/data/app_repository.dart';
import '../../session/data/session_controller.dart';
import '../../session/data/session_models.dart';

final currentParentProvider = Provider<ParentAccount?>((ref) {
  return ref.watch(sessionControllerProvider).parent;
});

final activeChildProvider = Provider<ChildProfile?>((ref) {
  return ref.watch(sessionControllerProvider).activeChild;
});

final materialsProvider = FutureProvider<List<CourseMaterial>>((ref) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    return const <CourseMaterial>[];
  }
  return ref.watch(appRepositoryProvider).listMaterials(childId: child.id);
});

final materialProvider = FutureProvider.family<CourseMaterial, String>((ref, materialId) async {
  return ref.watch(appRepositoryProvider).getMaterial(materialId);
});

final materialJobProvider = FutureProvider.family<MaterialParseJob, String>((ref, jobId) async {
  return ref.watch(appRepositoryProvider).getMaterialJob(jobId);
});

final knowledgePackProvider = FutureProvider.family<KnowledgePack, String>((ref, materialId) async {
  return ref.watch(appRepositoryProvider).getKnowledgePack(materialId);
});

final parentCoachingScriptProvider =
    FutureProvider.family<ParentCoachingScript, String>((ref, materialId) async {
  return ref.watch(appRepositoryProvider).getParentCoaching(materialId);
});

final lastSpeakingAttemptProvider = StateProvider<SpeakingAttempt?>((ref) => null);

final reviewTasksProvider = FutureProvider<List<ReviewTask>>((ref) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    return const <ReviewTask>[];
  }
  return ref.watch(appRepositoryProvider).listReviewTasks(childId: child.id);
});

final weeklyReportProvider = FutureProvider<WeeklyReport>((ref) async {
  final child = ref.watch(activeChildProvider);
  if (child == null) {
    throw StateError('No active child selected');
  }
  return ref.watch(appRepositoryProvider).getWeeklyReport(childId: child.id);
});
