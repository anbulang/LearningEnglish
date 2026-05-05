import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';
import 'package:learning_english_mobile/core/widgets/illustrated_surface.dart';

void main() {
  testWidgets('LessonCoverThumbnail can render inside a scrolling card row',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: <Widget>[
              const Row(
                children: <Widget>[
                  LessonCoverThumbnail(
                    title: 'Phonics Storybooks: Run, Hop, Go! & Quick!',
                    subtitle:
                        'Letter Rr and Letter Qq phonics practice for young children',
                    icon: Icons.record_voice_over_rounded,
                    accent: AppColors.skyBlue,
                  ),
                  SizedBox(width: AppSpacing.md),
                  Expanded(child: Text('待校对')),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.byType(LessonCoverThumbnail), findsOneWidget);
  });
}
