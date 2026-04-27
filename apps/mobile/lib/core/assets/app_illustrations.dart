class AppIllustrations {
  const AppIllustrations._();

  static const String heroLogin =
      'assets/images/heroes/login_parent_child_pack.png';
  static const String heroHome = 'assets/images/heroes/home_study_desk.png';
  static const String heroUpload =
      'assets/images/heroes/upload_worksheet_to_pack.png';
  static const String heroAiProcessing =
      'assets/images/heroes/ai_processing.png';
  static const String heroAiReady = 'assets/images/heroes/ai_ready.png';
  static const String heroAiRetry = 'assets/images/heroes/ai_retry.png';
  static const String heroLesson = 'assets/images/heroes/lesson_pack.png';
  static const String heroWeeklyGrowth =
      'assets/images/heroes/weekly_growth.png';
  static const String heroSpeakingPartner =
      'assets/images/heroes/speaking_partner.png';
  static const String heroParentCoaching =
      'assets/images/heroes/parent_coaching.png';

  static const String topicAnimals = 'assets/images/topics/animals.png';
  static const String topicNumbers = 'assets/images/topics/numbers.png';
  static const String topicPhonics = 'assets/images/topics/phonics.png';
  static const String topicColors = 'assets/images/topics/colors.png';
  static const String topicFruits = 'assets/images/topics/fruits.png';
  static const String topicFamily = 'assets/images/topics/family.png';
  static const String topicDialogue = 'assets/images/topics/dialogue.png';

  static const String stateEmpty = 'assets/images/states/empty.png';
  static const String stateError = 'assets/images/states/error.png';
  static const String stateSuccess = 'assets/images/states/success.png';
  static const String stateNetwork = 'assets/images/states/network.png';

  static const String vocabularyCat = 'assets/images/vocabulary/cat.png';
  static const String vocabularyDog = 'assets/images/vocabulary/dog.png';
  static const String vocabularyBird = 'assets/images/vocabulary/bird.png';
  static const String vocabularyApple = 'assets/images/vocabulary/apple.png';
  static const String vocabularyBanana = 'assets/images/vocabulary/banana.png';
  static const String vocabularyRed = 'assets/images/vocabulary/red.png';
  static const String vocabularyBlue = 'assets/images/vocabulary/blue.png';

  static String topicFor(String topic) {
    final normalized = topic.toLowerCase();
    if (_containsAny(
        normalized, const <String>['animal', 'zoo', 'pet', '动物', '宠物'])) {
      return topicAnimals;
    }
    if (_containsAny(
        normalized, const <String>['number', 'count', 'math', '数字', '数数'])) {
      return topicNumbers;
    }
    if (_containsAny(normalized,
        const <String>['phonic', 'letter', 'sound', '自然拼读', '字母', '发音'])) {
      return topicPhonics;
    }
    if (_containsAny(normalized, const <String>['color', 'colour', '颜色'])) {
      return topicColors;
    }
    if (_containsAny(normalized, const <String>['fruit', 'food', '水果', '食物'])) {
      return topicFruits;
    }
    if (_containsAny(
        normalized, const <String>['family', 'home', '家庭', '家人'])) {
      return topicFamily;
    }
    if (_containsAny(normalized, const <String>[
      'dialogue',
      'daily',
      'talk',
      'conversation',
      '对话',
      '日常'
    ])) {
      return topicDialogue;
    }
    return heroLesson;
  }

  static String? vocabularyFor(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized == 'cat') return vocabularyCat;
    if (normalized == 'dog') return vocabularyDog;
    if (normalized == 'bird') return vocabularyBird;
    if (normalized == 'apple') return vocabularyApple;
    if (normalized == 'banana') return vocabularyBanana;
    if (normalized == 'red') return vocabularyRed;
    if (normalized == 'blue') return vocabularyBlue;
    return null;
  }

  static bool _containsAny(String value, List<String> tokens) {
    return tokens.any(value.contains);
  }
}
