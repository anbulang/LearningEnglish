import 'package:flutter_riverpod/flutter_riverpod.dart';

final scanDraftProvider =
    StateNotifierProvider<ScanDraftController, ScanDraftState>((ref) {
  return ScanDraftController();
});

class ScanDraftState {
  const ScanDraftState({
    required this.pages,
    required this.autoEnhance,
  });

  final bool autoEnhance;
  final List<String> pages;

  ScanDraftState copyWith({
    List<String>? pages,
    bool? autoEnhance,
  }) {
    return ScanDraftState(
      pages: pages ?? this.pages,
      autoEnhance: autoEnhance ?? this.autoEnhance,
    );
  }
}

class ScanDraftController extends StateNotifier<ScanDraftState> {
  ScanDraftController()
      : super(
          const ScanDraftState(
            pages: <String>['worksheet-page-1.jpg', 'worksheet-page-2.jpg'],
            autoEnhance: true,
          ),
        );

  void toggleEnhance(bool value) {
    state = state.copyWith(autoEnhance: value);
  }

  void addPage() {
    final nextIndex = state.pages.length + 1;
    state = state.copyWith(
      pages: <String>[...state.pages, 'worksheet-page-$nextIndex.jpg'],
    );
  }

  void clear() {
    state = const ScanDraftState(pages: <String>[], autoEnhance: true);
  }
}
