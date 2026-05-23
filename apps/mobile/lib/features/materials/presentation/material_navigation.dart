import 'package:learning_english_contracts/contracts.dart';

String materialDestination(CourseMaterial material) {
  if (material.status == MaterialStatus.ready) {
    return '/lessons/${material.id}';
  }
  if (material.parseJobId.isNotEmpty) {
    return '/materials/review/${material.parseJobId}?materialId=${material.id}';
  }
  return '/materials';
}

CourseMaterial? firstReadyMaterial(List<CourseMaterial>? materials) {
  if (materials == null || materials.isEmpty) {
    return null;
  }
  for (final material in materials) {
    if (material.status == MaterialStatus.ready) {
      return material;
    }
  }
  return null;
}
