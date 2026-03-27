import 'package:dio/dio.dart';

String describeApiError(Object error, {String fallback = '请求失败，请稍后重试。'}) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail;
      }
      final message = data['message'];
      if (message is String && message.trim().isNotEmpty) {
        return message;
      }
    }
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.sendTimeout) {
      return '网络连接超时，请稍后重试。';
    }
    if (error.type == DioExceptionType.connectionError) {
      return '无法连接服务器，请检查网络或确认 API 已启动。';
    }
    if (error.message != null && error.message!.trim().isNotEmpty) {
      return error.message!;
    }
  }
  return fallback;
}
