import 'package:flutter/material.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: <Color>[AppColors.warmLinen, AppColors.softSheet],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: const <Widget>[
              CircleAvatar(
                radius: 44,
                backgroundColor: AppColors.paperWhite,
                child: Icon(Icons.auto_stories_rounded, color: AppColors.coralJam, size: 42),
              ),
              SizedBox(height: AppSpacing.lg),
              CircularProgressIndicator(),
              SizedBox(height: AppSpacing.md),
              Text('正在恢复家长会话...'),
            ],
          ),
        ),
      ),
    );
  }
}
