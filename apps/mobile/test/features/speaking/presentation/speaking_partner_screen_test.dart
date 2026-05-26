import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';
import 'package:learning_english_mobile/features/speaking/data/speaking_recorder_controller.dart';
import 'package:learning_english_mobile/features/speaking/presentation/speaking_partner_screen.dart';

void main() {
  testWidgets('speaking page shows target text and record action',
      (tester) async {
    await tester.pumpWidget(_buildTestApp());
    await tester.pumpAndSettle();

    expect(find.text('口语陪练'), findsOneWidget);
    expect(find.textContaining('开始录音'), findsOneWidget);
    expect(find.text('A rabbit can hop fast.'), findsOneWidget);
  });

  testWidgets('speaking page shows scored result', (tester) async {
    final attempt = SpeakingAttempt(
      id: 'attempt_test',
      childId: 'child_test',
      materialId: 'material_test',
      promptText: '跟读：A rabbit can hop fast.',
      targetText: 'A rabbit can hop fast.',
      audioUrl: 'http://testserver/audio.m4a',
      audioObjectKey: 'speaking_attempt/attempt_test/input.m4a',
      audioContentType: 'audio/mp4',
      audioSizeBytes: 10,
      audioDurationMs: 3000,
      transcript: 'A rabbit can hop fast.',
      pronunciationScore: 0.88,
      overallScore: 88,
      accuracyScore: 90,
      fluencyScore: 84,
      completenessScore: 94,
      feedback: '整体读得很清楚。',
      wordFeedback: const <SpeakingWordFeedback>[
        SpeakingWordFeedback(
          word: 'rabbit',
          score: 92,
          status: 'good',
          tip: '读得清楚。',
        ),
      ],
      suggestions: const <String>['再跟读一次 hop。'],
      provider: 'stub',
      rawResult: const <String, dynamic>{},
      failureReason: '',
      status: SpeakingAttemptStatus.scored,
    );

    await tester.pumpWidget(_buildTestApp(attempt: attempt));
    await tester.pumpAndSettle();

    expect(find.text('88'), findsOneWidget);
    expect(find.text('整体读得很清楚。'), findsOneWidget);
    expect(find.text('rabbit 92'), findsOneWidget);
  });

  testWidgets('speaking page disables submit and clear while recording',
      (tester) async {
    await tester.pumpWidget(
      _buildTestApp(
        recorderState: const SpeakingRecorderState(
          isRecording: true,
          audioPath: '/tmp/rabbit.m4a',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final stopButton =
        tester.widget<FilledButton>(find.widgetWithText(FilledButton, '停止录音'));
    final submitButton =
        tester.widget<FilledButton>(find.widgetWithText(FilledButton, '提交评分'));
    final clearButton = tester
        .widget<OutlinedButton>(find.widgetWithText(OutlinedButton, '清除录音'));

    expect(stopButton.onPressed, isNotNull);
    expect(submitButton.onPressed, isNull);
    expect(clearButton.onPressed, isNull);
  });

  testWidgets('speaking page stops polling after permanent fetch error',
      (tester) async {
    final requestOptions =
        RequestOptions(path: '/speaking-attempts/attempt_test');
    final repository = _FakeSpeakingRepository(
      fetchError: DioException(
        requestOptions: requestOptions,
        response: Response<Map<String, dynamic>>(
          requestOptions: requestOptions,
          statusCode: 404,
          data: <String, dynamic>{'detail': '录音记录不存在'},
        ),
      ),
    );

    await tester.pumpWidget(
      _buildTestApp(
        repository: repository,
        attempt: _attempt(status: SpeakingAttemptStatus.recordingUploaded),
      ),
    );
    await tester.pump();

    await tester.pump(const Duration(seconds: 3));
    await tester.pump();

    expect(repository.getAttemptCalls, 1);
    expect(find.text('录音记录不存在'), findsOneWidget);

    await tester.pump(const Duration(seconds: 3));
    await tester.pump();

    expect(repository.getAttemptCalls, 1);
  });
}

Widget _buildTestApp({
  SpeakingAttempt? attempt,
  _FakeSpeakingRepository? repository,
  SpeakingRecorderState? recorderState,
}) {
  final overrides = <Override>[
    appRepositoryProvider
        .overrideWithValue(repository ?? _FakeSpeakingRepository()),
    activeChildProvider.overrideWithValue(_childProfile()),
    lastSpeakingAttemptProvider.overrideWith((ref) => attempt),
  ];
  if (recorderState != null) {
    overrides.add(
      speakingRecorderControllerProvider.overrideWith(
        () => _FakeSpeakingRecorderController(recorderState),
      ),
    );
  }
  return ProviderScope(
    overrides: overrides,
    child: const MaterialApp(
      home: SpeakingPartnerScreen(materialId: 'material_test'),
    ),
  );
}

class _FakeSpeakingRepository extends AppRepository {
  _FakeSpeakingRepository({this.fetchError})
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final Object? fetchError;
  var getAttemptCalls = 0;

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return _material();
  }

  @override
  Future<SpeakingAttempt> getSpeakingAttempt(String attemptId) async {
    getAttemptCalls += 1;
    final error = fetchError;
    if (error != null) {
      throw error;
    }
    return _attempt(status: SpeakingAttemptStatus.scored);
  }
}

class _FakeSpeakingRecorderController extends SpeakingRecorderController {
  _FakeSpeakingRecorderController(this.initialState);

  final SpeakingRecorderState initialState;

  @override
  SpeakingRecorderState build() {
    return initialState;
  }

  @override
  Future<void> clear() async {
    state = const AsyncData(SpeakingRecorderState());
  }
}

ChildProfile _childProfile() {
  return const ChildProfile(
    id: 'child_test',
    name: 'Mia',
    avatarUrl: '',
    age: 6,
    level: 'starter',
    learningGoal: '课后复习更稳定',
    preferredReviewDurationMinutes: 10,
    parentNotes: '',
  );
}

CourseMaterial _material() {
  return CourseMaterial(
    id: 'material_test',
    childId: 'child_test',
    parseJobId: 'job_test',
    teacherName: 'Emma',
    lessonDate: DateTime(2026, 5, 25),
    title: 'Run, Hop, Go!',
    topic: 'Phonics Rr',
    status: MaterialStatus.ready,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: '',
    tags: const <String>[],
    learningAssets: const <LearningAsset>[
      LearningAsset(
        id: 'asset_rabbit',
        text: 'A rabbit can hop fast.',
        kind: 'sentence',
        translation: '兔子能跳得很快。',
        pronunciationText: 'A rabbit can hop fast.',
        primaryAccent: 'us',
      ),
    ],
  );
}

SpeakingAttempt _attempt({required SpeakingAttemptStatus status}) {
  return SpeakingAttempt(
    id: 'attempt_test',
    childId: 'child_test',
    materialId: 'material_test',
    promptText: '跟读：A rabbit can hop fast.',
    targetText: 'A rabbit can hop fast.',
    audioUrl: 'http://testserver/audio.m4a',
    audioObjectKey: 'speaking_attempt/attempt_test/input.m4a',
    audioContentType: 'audio/mp4',
    audioSizeBytes: 10,
    audioDurationMs: 3000,
    transcript: '',
    pronunciationScore: null,
    overallScore: null,
    accuracyScore: null,
    fluencyScore: null,
    completenessScore: null,
    feedback: '',
    wordFeedback: const <SpeakingWordFeedback>[],
    suggestions: const <String>[],
    provider: 'stub',
    rawResult: const <String, dynamic>{},
    failureReason: '',
    status: status,
  );
}
