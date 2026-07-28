import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/phone_binding_screen.dart';
import '../../features/coaching/presentation/parent_coaching_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/lessons/presentation/lesson_detail_screen.dart';
import '../../features/materials/presentation/material_review_screen.dart';
import '../../features/phonics/presentation/phonics_lesson_screen.dart';
import '../../features/phonics/presentation/phonics_unit_list_screen.dart';
import '../../features/materials/presentation/materials_library_screen.dart';
import '../../features/materials/presentation/scan_upload_screen.dart';
import '../../features/profiles/presentation/profile_screen.dart';
import '../../features/reports/presentation/reports_screen.dart';
import '../../features/review/presentation/review_runner_screen.dart';
import '../../features/review/presentation/review_tasks_screen.dart';
import '../../features/session/data/session_controller.dart';
import '../../features/session/data/session_models.dart';
import '../../features/session/presentation/splash_screen.dart';
import '../../features/settings/presentation/server_settings_screen.dart';
import '../../features/speaking/presentation/speaking_partner_screen.dart';
import '../shell/app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  // Only rebuild the router when the auth STAGE changes. Watching the whole
  // session state would recreate the GoRouter on any child-data change (e.g. an
  // accent toggle), resetting navigation back to /home.
  final stage = ref.watch(sessionControllerProvider.select((s) => s.stage));
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final location = state.uri.path;
      final isAuthRoute = location.startsWith('/auth');
      // Server-address settings must stay reachable in every stage (pre-login,
      // and while stuck on phone binding) so a tester can always repoint the app.
      if (location == '/settings/server') {
        return null;
      }
      if (stage == SessionStage.bootstrapping) {
        return location == '/splash' ? null : '/splash';
      }
      if (stage == SessionStage.signedOut) {
        return isAuthRoute ? null : '/auth/login';
      }
      if (stage == SessionStage.phoneBindingRequired) {
        return location == '/auth/bind' ? null : '/auth/bind';
      }
      if (stage == SessionStage.authenticated &&
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
      GoRoute(
        path: '/settings/server',
        builder: (context, state) => const ServerSettingsScreen(),
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
            path: '/phonics',
            builder: (context, state) => const PhonicsUnitListScreen(),
            routes: <RouteBase>[
              GoRoute(
                path: 'unit/:unitId',
                builder: (context, state) => PhonicsLessonScreen(
                  unitId: state.pathParameters['unitId'] ?? '',
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
