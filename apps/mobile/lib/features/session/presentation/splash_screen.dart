import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            CircularProgressIndicator(),
            SizedBox(height: AppSpacing.md),
            Text('正在恢复家长会话...'),
          ],
        ),
      ),
    );
  }
}
