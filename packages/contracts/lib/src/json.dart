typedef JsonMap = Map<String, dynamic>;

DateTime? dateTimeFromJson(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.parse(value as String);
}

List<String> stringListFromJson(dynamic value) {
  if (value == null) {
    return const <String>[];
  }
  return List<String>.from(value as List<dynamic>);
}

double? doubleFromJson(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is double) {
    return value;
  }
  if (value is int) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}
