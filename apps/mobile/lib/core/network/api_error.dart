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
      return '网络连接超时，请稍后重试。${_debugRequestHint(error)}';
    }
    if (error.type == DioExceptionType.connectionError) {
      return '无法连接服务器，请检查网络或确认 API 已启动。${_debugRequestHint(error)}';
    }
    if (error.message != null && error.message!.trim().isNotEmpty) {
      return '${error.message!}${_debugRequestHint(error)}';
    }
  }
  return fallback;
}

bool isNotFoundApiError(Object error) {
  return error is DioException && error.response?.statusCode == 404;
}

String _debugRequestHint(DioException error) {
  const showDebugNetworkErrors = bool.fromEnvironment(
    'SHOW_DEBUG_NETWORK_ERRORS',
    defaultValue: false,
  );
  if (!showDebugNetworkErrors) {
    return '';
  }
  final uri = error.requestOptions.uri.toString();
  final message = error.message?.trim();
  final parts = <String>[
    '请求地址：$uri',
    '错误类型：${error.type.name}',
    if (message != null && message.isNotEmpty) '底层错误：$message',
  ];
  return '\n\n调试信息：${parts.join('；')}';
}
