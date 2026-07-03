import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_mobile/core/widgets/audio_play_button.dart';

void main() {
  testWidgets('is disabled and labelled unavailable when url is empty',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: AudioPlayButton(url: '', label: '听标准音')),
        ),
      ),
    );

    final button =
        tester.widget<OutlinedButton>(find.byType(OutlinedButton));
    expect(button.onPressed, isNull);
    expect(find.text('发音生成中'), findsOneWidget);
  });

  testWidgets('is enabled and shows its label when url is present',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AudioPlayButton(
              url: 'https://example.test/queen.m4a',
              label: '听标准音',
            ),
          ),
        ),
      ),
    );

    final button =
        tester.widget<OutlinedButton>(find.byType(OutlinedButton));
    expect(button.onPressed, isNotNull);
    expect(find.text('听标准音'), findsOneWidget);
  });

  testWidgets('icon-only variant is disabled when url is empty',
      (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: AudioPlayButton(url: '')),
        ),
      ),
    );

    final button = tester.widget<IconButton>(find.byType(IconButton));
    expect(button.onPressed, isNull);
  });
}
