import 'package:learning_english_contracts/contracts.dart';

abstract class MaterialsRepository {
  Future<List<CourseMaterial>> listMaterials({required String childId});
  Future<MaterialParseJob> getMaterialJob(String jobId);
  Future<KnowledgePack> getKnowledgePack(String materialId);
  Future<List<ReviewTask>> listReviewTasks({
    required String childId,
    String? materialId,
  });
}
