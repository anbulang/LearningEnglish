import 'dart:typed_data';

import 'package:dio/dio.dart';

typedef FakeDioHandler = ResponseBody Function(RequestOptions options);

class SequenceDioAdapter implements HttpClientAdapter {
  SequenceDioAdapter(this._handlers);

  final List<FakeDioHandler> _handlers;
  final requests = <RequestOptions>[];
  var _index = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    if (_index >= _handlers.length) {
      throw StateError('No response configured for request #$_index');
    }
    final handler = _handlers[_index];
    _index += 1;
    return handler(options);
  }
}
