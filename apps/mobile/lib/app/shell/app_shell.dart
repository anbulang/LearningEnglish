import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../responsive/adaptive_layout.dart';

class AppShell extends StatelessWidget {
  const AppShell({
    required this.child,
    required this.location,
    super.key,
  });

  final Widget child;
  final String location;

  static const List<_ShellDestination> _destinations = <_ShellDestination>[
    _ShellDestination(label: '首页', icon: Icons.home_rounded, route: '/home'),
    _ShellDestination(
      label: '资料库',
      icon: Icons.folder_copy_rounded,
      route: '/materials',
    ),
    _ShellDestination(
      label: '复习',
      icon: Icons.auto_stories_rounded,
      route: '/review',
    ),
    _ShellDestination(
      label: '报告',
      icon: Icons.query_stats_rounded,
      route: '/reports',
    ),
    _ShellDestination(
      label: '我的',
      icon: Icons.family_restroom_rounded,
      route: '/profile',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);
    final selectedIndex = _selectedIndex(location);

    if (formFactor == AppFormFactor.phone) {
      return Scaffold(
        body: child,
        bottomNavigationBar: NavigationBar(
          selectedIndex: selectedIndex,
          onDestinationSelected: (index) {
            context.go(_destinations[index].route);
          },
          destinations: _destinations
              .map(
                (item) => NavigationDestination(
                  icon: Icon(item.icon),
                  label: item.label,
                ),
              )
              .toList(),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.warmLinen,
      body: SafeArea(
        child: Row(
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: NavigationRail(
                backgroundColor: AppColors.paperWhite,
                selectedIndex: selectedIndex,
                onDestinationSelected: (index) {
                  context.go(_destinations[index].route);
                },
                labelType: formFactor.isFullTablet
                    ? NavigationRailLabelType.all
                    : NavigationRailLabelType.selected,
                destinations: _destinations
                    .map(
                      (item) => NavigationRailDestination(
                        icon: Icon(item.icon),
                        label: Text(item.label),
                      ),
                    )
                    .toList(),
              ),
            ),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }

  int _selectedIndex(String currentLocation) {
    // Lesson detail lives outside the shell route table but belongs to the
    // materials section, so keep the 资料库 tab highlighted there.
    if (currentLocation.startsWith('/lessons')) {
      final materialsIndex =
          _destinations.indexWhere((item) => item.route == '/materials');
      if (materialsIndex != -1) {
        return materialsIndex;
      }
    }
    final index = _destinations.indexWhere(
      (item) => currentLocation == item.route || currentLocation.startsWith('${item.route}/'),
    );
    return index == -1 ? 0 : index;
  }
}

class _ShellDestination {
  const _ShellDestination({
    required this.label,
    required this.icon,
    required this.route,
  });

  final IconData icon;
  final String label;
  final String route;
}
