import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

final scanDraftProvider =
    StateNotifierProvider<ScanDraftController, ScanDraftState>((ref) {
  return ScanDraftController();
});

class ScanDraftState {
  const ScanDraftState({
    required this.pages,
    required this.autoEnhance,
    required this.title,
    required this.teacherName,
    required this.topic,
    required this.lessonDate,
  });

  final bool autoEnhance;
  final DateTime lessonDate;
  final List<ScanDraftPage> pages;
  final String teacherName;
  final String title;
  final String topic;

  ScanDraftState copyWith({
    List<ScanDraftPage>? pages,
    bool? autoEnhance,
    String? title,
    String? teacherName,
    String? topic,
    DateTime? lessonDate,
  }) {
    return ScanDraftState(
      pages: pages ?? this.pages,
      autoEnhance: autoEnhance ?? this.autoEnhance,
      title: title ?? this.title,
      teacherName: teacherName ?? this.teacherName,
      topic: topic ?? this.topic,
      lessonDate: lessonDate ?? this.lessonDate,
    );
  }
}

class ScanDraftController extends StateNotifier<ScanDraftState> {
  ScanDraftController()
      : super(
          ScanDraftState(
            pages: const <ScanDraftPage>[],
            autoEnhance: true,
            title: '',
            teacherName: '',
            topic: '',
            lessonDate: DateTime.now(),
          ),
        );

  void toggleEnhance(bool value) {
    state = state.copyWith(autoEnhance: value);
  }

  void setTitle(String value) {
    state = state.copyWith(title: value);
  }

  void setTeacherName(String value) {
    state = state.copyWith(teacherName: value);
  }

  void setTopic(String value) {
    state = state.copyWith(topic: value);
  }

  void setLessonDate(DateTime value) {
    state = state.copyWith(lessonDate: value);
  }

  void setPages(List<ScanDraftPage> value) {
    state = state.copyWith(pages: value);
  }

  void clear() {
    state = ScanDraftState(
      pages: const <ScanDraftPage>[],
      autoEnhance: true,
      title: '',
      teacherName: '',
      topic: '',
      lessonDate: DateTime.now(),
    );
  }
}

class ScanDraftPage {
  const ScanDraftPage({
    required this.file,
    required this.sourceType,
  });

  final XFile file;
  final String sourceType;

  String get sourceLabel => sourceType == 'camera' ? '相机拍摄' : '相册选择';
}
