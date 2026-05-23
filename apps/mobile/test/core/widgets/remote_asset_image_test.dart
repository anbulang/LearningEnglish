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
