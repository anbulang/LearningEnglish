import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_mobile/core/widgets/remote_asset_image.dart';

void main() {
  test('detects svg worksheet asset urls', () {
    expect(
      isSvgAssetUrl('http://127.0.0.1:8000/mock-media/hn014/images/queen.svg'),
      isTrue,
    );
    expect(
      isSvgAssetUrl(
        'http://127.0.0.1:8000/mock-media/hn014/images/queen.svg?cache=1',
      ),
      isTrue,
    );
    expect(
      isSvgAssetUrl('http://127.0.0.1:8000/uploads/page-1.jpg'),
      isFalse,
    );
  });

  test('detects data image urls', () {
    expect(isDataImageUrl('data:image/png;base64,AAA='), isTrue);
    expect(isDataImageUrl('https://example.test/image.png'), isFalse);
  });

  testWidgets('renders base64 data image urls', (tester) async {
    const onePixelPng =
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lTQkWQAAAABJRU5ErkJggg==';
    await tester.pumpWidget(
      MaterialApp(
        home: RemoteAssetImage(
          url: 'data:image/png;base64,${base64.normalize(onePixelPng)}',
          width: 64,
          height: 64,
          errorIcon: Icons.image_outlined,
        ),
      ),
    );

    expect(find.byType(Image), findsOneWidget);
    expect(find.byIcon(Icons.image_outlined), findsNothing);
  });

  testWidgets('shows fallback for missing worksheet asset url', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: RemoteAssetImage(
          url: '',
          width: 64,
          height: 64,
          errorIcon: Icons.image_outlined,
        ),
      ),
    );

    expect(find.byIcon(Icons.image_outlined), findsOneWidget);
  });
}
