import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';

final activeChildProvider = Provider<ChildProfile>((ref) {
  return ChildProfile(
    id: 'child_demo_1',
    name: 'Mia',
    avatarUrl: '',
    age: 6,
    level: 'Starter',
    learningGoal: '会说课堂高频问答和 40 个基础词',
    preferredReviewDurationMinutes: 10,
    parentNotes: '晚上 7 点后状态更稳定',
  );
});

final materialsProvider = Provider<List<CourseMaterial>>((ref) {
  return <CourseMaterial>[
    CourseMaterial(
      id: 'material_demo_1',
      childId: 'child_demo_1',
      teacherName: 'Emma',
      lessonDate: DateTime(2026, 3, 24),
      title: 'Animals Around Me',
      topic: '动物',
      status: MaterialStatus.ready,
      sourceImages: const <String>['demo://worksheet-1'],
      pdfUrl: 'demo://worksheet-1.pdf',
      ocrText: 'cat dog bird What is this? It is a cat.',
      tags: const <String>['动物', '问答'],
    ),
    CourseMaterial(
      id: 'material_demo_2',
      childId: 'child_demo_1',
      teacherName: 'Emma',
      lessonDate: DateTime(2026, 3, 22),
      title: 'Fruit Basket',
      topic: '水果',
      status: MaterialStatus.needsReview,
      sourceImages: const <String>['demo://worksheet-2'],
      pdfUrl: 'demo://worksheet-2.pdf',
      ocrText: 'apple banana orange Do you like apples?',
      tags: const <String>['水果', '口语'],
    ),
  ];
});

final materialJobProvider = Provider<MaterialParseJob>((ref) {
  return MaterialParseJob(
    id: 'job_demo_2',
    materialId: 'material_demo_2',
    status: JobStatus.needsReview,
    confidenceSummary: '2 个单词识别置信度偏低，需要家长确认。',
    warnings: const <String>['banana 可能被误识别为 bannna'],
    startedAt: DateTime(2026, 3, 25, 10, 30),
    finishedAt: DateTime(2026, 3, 25, 10, 31),
    draftTitle: 'Fruit Basket',
    draftTopic: '水果',
    draftVocabulary: const <String>['apple', 'banana', 'orange'],
    draftSentences: const <String>['Do you like apples?', 'Yes, I do.'],
  );
});

final knowledgePackProvider = Provider<KnowledgePack>((ref) {
  return KnowledgePack(
    id: 'knowledge_demo_1',
    materialId: 'material_demo_1',
    topic: '动物',
    difficultyBand: DifficultyBand.repeat,
    lessonSummary: '本课围绕常见动物词汇和 What is this? 句型展开。',
    reviewRecommendation: '先词卡，再听音选图，最后家长提问。',
    vocabularyItems: const <VocabularyItem>[
      VocabularyItem(
        id: 'word_cat',
        knowledgePackId: 'knowledge_demo_1',
        word: 'cat',
        phonics: '/kæt/',
        meaningCn: '猫',
        imageUrl: '',
        audioUrl: '',
        exampleSentence: 'It is a cat.',
      ),
      VocabularyItem(
        id: 'word_dog',
        knowledgePackId: 'knowledge_demo_1',
        word: 'dog',
        phonics: '/dɔːɡ/',
        meaningCn: '狗',
        imageUrl: '',
        audioUrl: '',
        exampleSentence: 'This is a dog.',
      ),
      VocabularyItem(
        id: 'word_bird',
        knowledgePackId: 'knowledge_demo_1',
        word: 'bird',
        phonics: '/bɝːd/',
        meaningCn: '鸟',
        imageUrl: '',
        audioUrl: '',
        exampleSentence: 'I can see a bird.',
      ),
    ],
    sentencePatterns: const <SentencePattern>[
      SentencePattern(
        id: 'sentence_1',
        knowledgePackId: 'knowledge_demo_1',
        sentence: 'What is this?',
        meaningCn: '这是什么？',
        usageType: 'question',
        audioUrl: '',
      ),
      SentencePattern(
        id: 'sentence_2',
        knowledgePackId: 'knowledge_demo_1',
        sentence: 'It is a cat.',
        meaningCn: '它是一只猫。',
        usageType: 'answer',
        audioUrl: '',
      ),
    ],
  );
});

final reviewTasksProvider = Provider<List<ReviewTask>>((ref) {
  return <ReviewTask>[
    ReviewTask(
      id: 'task_1',
      childId: 'child_demo_1',
      materialId: 'material_demo_1',
      taskType: TaskType.flashcard,
      difficulty: 'recognition',
      contentJson: const <String, dynamic>{
        'prompt': '看词卡并跟读',
        'word': 'cat',
        'hint': '点击听标准发音',
      },
      dueDate: DateTime(2026, 3, 25),
      status: ReviewTaskStatus.pending,
    ),
    ReviewTask(
      id: 'task_2',
      childId: 'child_demo_1',
      materialId: 'material_demo_1',
      taskType: TaskType.listenChoice,
      difficulty: 'repeat',
      contentJson: const <String, dynamic>{
        'prompt': '听音选图',
        'choices': <String>['cat', 'dog', 'bird'],
        'correct_answer': 'cat',
      },
      dueDate: DateTime(2026, 3, 25),
      status: ReviewTaskStatus.pending,
    ),
    ReviewTask(
      id: 'task_3',
      childId: 'child_demo_1',
      materialId: 'material_demo_1',
      taskType: TaskType.matchChoice,
      difficulty: 'comprehension',
      contentJson: const <String, dynamic>{
        'prompt': '问句和答句配对',
        'left': <String>['What is this?'],
        'right': <String>['It is a cat.'],
      },
      dueDate: DateTime(2026, 3, 25),
      status: ReviewTaskStatus.pending,
    ),
  ];
});

final weeklyReportProvider = Provider<WeeklyReport>((ref) {
  return WeeklyReport(
    id: 'report_demo_1',
    childId: 'child_demo_1',
    weekStart: DateTime(2026, 3, 23),
    weekEnd: DateTime(2026, 3, 29),
    completedSessions: 4,
    reviewedWords: 18,
    speakingAttempts: 3,
    weakItems: const <String>['bird', 'What is this?'],
    recommendedActions: const <String>[
      '今晚先复习 3 张动物词卡',
      '再用 What is this? 做 2 轮问答',
    ],
  );
});
