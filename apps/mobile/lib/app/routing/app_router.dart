import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/coaching/presentation/parent_coaching_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/lessons/presentation/lesson_detail_screen.dart';
import '../../features/materials/presentation/material_review_screen.dart';
import '../../features/materials/presentation/materials_library_screen.dart';
import '../../features/materials/presentation/scan_upload_screen.dart';
import '../../features/profiles/presentation/profile_screen.dart';
import '../../features/review/presentation/review_runner_screen.dart';
import '../../features/review/presentation/review_tasks_screen.dart';
import '../../features/speaking/presentation/speaking_partner_screen.dart';
import '../shell/app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/home',
    routes: <RouteBase>[
      ShellRoute(
        builder: (context, state, child) {
          return AppShell(
            location: state.uri.path,
            child: child,
          );
        },
        routes: <RouteBase>[
          GoRoute(
            path: '/home',
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            path: '/materials',
            builder: (context, state) => const MaterialsLibraryScreen(),
            routes: <RouteBase>[
              GoRoute(
                path: 'scan',
                builder: (context, state) => const ScanUploadScreen(),
              ),
              GoRoute(
                path: 'review',
                builder: (context, state) => const MaterialReviewScreen(),
              ),
            ],
          ),
          GoRoute(
            path: '/lessons/:materialId',
            builder: (context, state) {
              return LessonDetailScreen(
                materialId: state.pathParameters['materialId'] ?? 'material_demo_1',
              );
            },
          ),
          GoRoute(
            path: '/review',
            builder: (context, state) => const ReviewTasksScreen(),
            routes: <RouteBase>[
              GoRoute(
                path: 'session/:materialId',
                builder: (context, state) => ReviewRunnerScreen(
                  materialId: state.pathParameters['materialId'] ?? 'material_demo_1',
                ),
              ),
              GoRoute(
                path: 'speaking/:materialId',
                builder: (context, state) => SpeakingPartnerScreen(
                  materialId: state.pathParameters['materialId'] ?? 'material_demo_1',
                ),
              ),
              GoRoute(
                path: 'coaching/:materialId',
                builder: (context, state) => ParentCoachingScreen(
                  materialId: state.pathParameters['materialId'] ?? 'material_demo_1',
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => const ReviewTasksScreen(reportMode: true),
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
});
