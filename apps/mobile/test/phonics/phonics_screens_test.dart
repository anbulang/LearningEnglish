import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/phonics/presentation/phonics_lesson_screen.dart';
import 'package:learning_english_mobile/features/phonics/presentation/phonics_unit_list_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';

void main() {
  testWidgets('unit list renders course + units and locks locked units',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 1600);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildApp(const PhonicsUnitListScreen()),
    );
    await tester.pumpAndSettle();

    expect(find.text('PEP 三上・自然拼读'), findsOneWidget);
    expect(find.text('字母 a b c d 与短音 a'), findsOneWidget);
    expect(find.text('后续单元（待解锁）'), findsOneWidget);

    // The unlocked unit is tappable (wrapped in an InkWell); the locked one is
    // deliberately not.
    expect(
      find.ancestor(
        of: find.text('字母 a b c d 与短音 a'),
        matching: find.byType(InkWell),
      ),
      findsOneWidget,
    );
    expect(
      find.ancestor(
        of: find.text('后续单元（待解锁）'),
        matching: find.byType(InkWell),
      ),
      findsNothing,
    );
  });

  testWidgets('lesson stepper renders the first 听音识音 stage', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 2400);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _buildApp(const PhonicsLessonScreen(unitId: 'phonics_l1_u1')),
    );
    await tester.pumpAndSettle();

    expect(find.text('第 1 步 / 共 4 步'), findsOneWidget);
    expect(find.text('听一听每个字母的发音，跟着读一遍。'), findsOneWidget);
    expect(find.text('/æ/'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '继续'), findsOneWidget);
  });
}

Widget _buildApp(Widget home) {
  return ProviderScope(
    overrides: <Override>[
      appRepositoryProvider.overrideWithValue(_FakePhonicsRepository()),
      activeChildProvider.overrideWithValue(_childProfile()),
    ],
    child: MaterialApp(home: home),
  );
}

class _FakePhonicsRepository extends AppRepository {
  _FakePhonicsRepository()
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  @override
  Future<PhonicsUnitListResponse> getPhonicsUnits(String childId) async {
    return PhonicsUnitListResponse.fromJson(_unitListJson);
  }

  @override
  Future<PhonicsUnitDetailResponse> getPhonicsUnit(
    String unitId,
    String childId,
  ) async {
    return PhonicsUnitDetailResponse.fromJson(_unitDetailJson);
  }
}

ChildProfile _childProfile() {
  return const ChildProfile(
    id: 'child_test',
    name: 'Mia',
    avatarUrl: '',
    age: 8,
    level: 'starter',
    learningGoal: '学会自然拼读',
    preferredReviewDurationMinutes: 10,
    parentNotes: '',
  );
}

const Map<String, dynamic> _unitListJson = <String, dynamic>{
  'course': <String, dynamic>{
    'id': 'course_pep_g3',
    'title': 'PEP 三上・自然拼读',
    'description': '对齐人教版三年级上册的自然拼读课程。',
  },
  'units': <dynamic>[
    <String, dynamic>{
      'id': 'phonics_l1_u1',
      'unit_code': 'L1-U1',
      'sequence_order': 1,
      'title': '字母 a b c d 与短音 a',
      'subtitle': '认识 a、b、c、d 的发音，学会拼读带短音 a 的单词',
      'level': '1',
      'media_status': 'pending',
      'status': 'unlocked',
      'decoding_accuracy': 0.0,
    },
    <String, dynamic>{
      'id': 'phonics_l1_u2',
      'unit_code': 'L1-U2',
      'sequence_order': 2,
      'title': '后续单元（待解锁）',
      'subtitle': '完成上一课后解锁',
      'level': '1',
      'media_status': 'pending',
      'status': 'locked',
      'decoding_accuracy': 0.0,
    },
  ],
  'next_unit_id': 'phonics_l1_u1',
};

const Map<String, dynamic> _unitDetailJson = <String, dynamic>{
  'unit': <String, dynamic>{
    'id': 'phonics_l1_u1',
    'unit_code': 'L1-U1',
    'sequence_order': 1,
    'title': '字母 a b c d 与短音 a',
    'subtitle': '认识 a、b、c、d 的发音，学会拼读带短音 a 的单词',
    'level': '1',
    'vowel_focus': 'short_a',
    'letters': <dynamic>['a', 'b', 'c', 'd'],
    'media_status': 'pending',
  },
  'sound_cards': <dynamic>[
    <String, dynamic>{
      'id': 'card_short_a',
      'card_type': 'vowel',
      'letter': 'a',
      'phoneme': '/æ/',
      'keyword': 'apple',
      'keyword_cn': '苹果',
      'articulation_cue': '嘴巴张大，发短促的 ae 音。',
      'common_spellings': <dynamic>['a'],
      'speakable_sound': 'The short a sound.',
      'example_words': <dynamic>[
        <String, dynamic>{'text': 'apple', 'cn': '苹果'},
        <String, dynamic>{'text': 'ant', 'cn': '蚂蚁'},
      ],
      'sound_audio_url': '',
      'sound_tts_status': 'pending',
      'keyword_audio_url': '',
      'keyword_tts_status': 'pending',
    },
    <String, dynamic>{
      'id': 'card_b',
      'card_type': 'consonant',
      'letter': 'b',
      'phoneme': '/b/',
      'keyword': 'bag',
      'keyword_cn': '书包',
      'articulation_cue': '双唇闭紧再张开发 b 音。',
      'common_spellings': <dynamic>['b'],
      'speakable_sound': 'The b sound.',
      'example_words': <dynamic>[
        <String, dynamic>{'text': 'bag', 'cn': '书包'},
      ],
      'sound_audio_url': '',
      'sound_tts_status': 'pending',
      'keyword_audio_url': '',
      'keyword_tts_status': 'pending',
    },
    <String, dynamic>{
      'id': 'card_c',
      'card_type': 'consonant',
      'letter': 'c',
      'phoneme': '/k/',
      'keyword': 'cat',
      'keyword_cn': '猫',
      'articulation_cue': '舌根抬起发 k 音。',
      'common_spellings': <dynamic>['c', 'k'],
      'speakable_sound': 'The c sound.',
      'example_words': <dynamic>[
        <String, dynamic>{'text': 'cat', 'cn': '猫'},
      ],
      'sound_audio_url': '',
      'sound_tts_status': 'pending',
      'keyword_audio_url': '',
      'keyword_tts_status': 'pending',
    },
    <String, dynamic>{
      'id': 'card_d',
      'card_type': 'consonant',
      'letter': 'd',
      'phoneme': '/d/',
      'keyword': 'dog',
      'keyword_cn': '狗',
      'articulation_cue': '舌尖顶上齿龈发 d 音。',
      'common_spellings': <dynamic>['d'],
      'speakable_sound': 'The d sound.',
      'example_words': <dynamic>[
        <String, dynamic>{'text': 'dog', 'cn': '狗'},
      ],
      'sound_audio_url': '',
      'sound_tts_status': 'pending',
      'keyword_audio_url': '',
      'keyword_tts_status': 'pending',
    },
  ],
  'decodable_words': <dynamic>[
    <String, dynamic>{
      'id': 'w_dad',
      'text': 'dad',
      'segments': <dynamic>['d', 'a', 'd'],
      'cn': '爸爸',
      'kind': 'real',
      'audio_url': '',
      'tts_status': 'pending',
    },
  ],
  'sentences': <dynamic>[],
  'heart_words': <dynamic>[
    <String, dynamic>{'text': 'I', 'cn': '我', 'audio_url': '', 'tts_status': 'pending'},
    <String, dynamic>{'text': 'a', 'cn': '一（个）', 'audio_url': '', 'tts_status': 'pending'},
  ],
  'first_sound_items': <dynamic>[
    <String, dynamic>{
      'id': 'fs_dad',
      'word_id': 'w_dad',
      'text': 'dad',
      'cn': '爸爸',
      'answer': 'd',
      'options': <dynamic>['d', 'a', 'c'],
      'audio_url': '',
    },
  ],
  'steps': <dynamic>[
    <String, dynamic>{
      'key': 'sound_intro',
      'practice_type': 'none',
      'title': '听音・识音',
      'instruction': '听一听每个字母的发音，跟着读一遍。',
      'card_ids': <dynamic>['card_short_a', 'card_b', 'card_c', 'card_d'],
      'word_ids': <dynamic>[],
      'item_ids': <dynamic>[],
      'heart_words': <dynamic>[],
    },
    <String, dynamic>{
      'key': 'first_sound',
      'practice_type': 'first_sound_tap',
      'title': '听音・圈首音',
      'instruction': '听这个单词，点出它的第一个音是哪个字母。',
      'card_ids': <dynamic>[],
      'word_ids': <dynamic>[],
      'item_ids': <dynamic>['fs_dad'],
      'heart_words': <dynamic>[],
    },
    <String, dynamic>{
      'key': 'blending',
      'practice_type': 'blend_word_asr',
      'title': '拼一拼・读出来',
      'instruction': '把字母连起来读，然后录音。',
      'card_ids': <dynamic>[],
      'word_ids': <dynamic>['w_dad'],
      'item_ids': <dynamic>[],
      'heart_words': <dynamic>[],
    },
    <String, dynamic>{
      'key': 'heart_word',
      'practice_type': 'none',
      'title': '高频词',
      'instruction': '这些词要直接认读。',
      'card_ids': <dynamic>[],
      'word_ids': <dynamic>[],
      'item_ids': <dynamic>[],
      'heart_words': <dynamic>['I', 'a'],
    },
  ],
  'progress': <String, dynamic>{
    'unit_id': 'phonics_l1_u1',
    'status': 'unlocked',
    'decoding_accuracy': 0.0,
    'first_sound_accuracy': 0.0,
    'grapheme_scores': <String, dynamic>{},
    'attempts_count': 0,
    'blended_words': <dynamic>[],
    'mastered': false,
  },
};
