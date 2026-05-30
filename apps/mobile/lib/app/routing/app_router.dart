import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/phone_binding_screen.dart';
import '../../features/coaching/presentation/parent_coaching_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/lessons/presentation/lesson_detail_screen.dart';
import '../../features/materials/presentation/material_review_screen.dart';
import '../../features/materials/presentation/materials_library_screen.dart';
import '../../features/materials/presentation/scan_upload_screen.dart';
import '../../features/profiles/presentation/profile_screen.dart';
import '../../features/reports/presentation/reports_screen.dart';
import '../../features/review/presentation/review_runner_screen.dart';
import '../../features/review/presentation/review_tasks_screen.dart';
import '../../features/session/data/session_controller.dart';
import '../../features/session/data/session_models.dart';
import '../../features/session/presentation/splash_screen.dart';
import '../../features/speaking/presentation/speaking_partner_screen.dart';
import '../shell/app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final session = ref.watch(sessionControllerProvider);
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final location = state.uri.path;
      final isAuthRoute = location.startsWith('/auth');
      if (session.stage == SessionStage.bootstrapping) {
        return location == '/splash' ? null : '/splash';
      }
      if (session.stage == SessionStage.signedOut) {
        return isAuthRoute ? null : '/auth/login';
      }
      if (session.stage == SessionStage.phoneBindingRequired) {
        return location == '/auth/bind' ? null : '/auth/bind';
      }
      if (session.stage == SessionStage.authenticated &&
          (location == '/splash' || isAuthRoute)) {
        return '/home';
      }
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/auth/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/auth/bind',
        builder: (context, state) => const PhoneBindingScreen(),
      ),
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
                path: 'review/:jobId',
                builder: (context, state) => MaterialReviewScreen(
                  jobId: state.pathParameters['jobId'] ?? '',
                  materialId: state.uri.queryParameters['materialId'] ?? '',
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/lessons/:materialId',
            builder: (context, state) {
              return LessonDetailScreen(
                materialId: state.pathParameters['materialId'] ?? '',
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
                  materialId: state.pathParameters['materialId'] ?? '',
                ),
              ),
              GoRoute(
                path: 'speaking/:materialId',
                builder: (context, state) => SpeakingPartnerScreen(
                  materialId: state.pathParameters['materialId'] ?? '',
                ),
              ),
              GoRoute(
                path: 'coaching/:materialId',
                builder: (context, state) => ParentCoachingScreen(
                  materialId: state.pathParameters['materialId'] ?? '',
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => const ReportsScreen(),
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
