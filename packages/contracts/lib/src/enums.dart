enum MaterialStatus {
  uploaded('uploaded'),
  processing('processing'),
  needsReview('needs_review'),
  ready('ready'),
  archived('archived');

  const MaterialStatus(this.value);

  final String value;

  static MaterialStatus fromJson(String value) {
    return MaterialStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => MaterialStatus.uploaded,
    );
  }
}

enum JobStatus {
  queued('queued'),
  processing('processing'),
  needsReview('needs_review'),
  ready('ready'),
  failed('failed');

  const JobStatus(this.value);

  final String value;

  static JobStatus fromJson(String value) {
    return JobStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => JobStatus.queued,
    );
  }
}

enum TaskType {
  flashcard('flashcard'),
  listenChoice('listen_choice'),
  matchChoice('match_choice'),
  speakingPrompt('speaking_prompt'),
  parentCoaching('parent_coaching');

  const TaskType(this.value);

  final String value;

  static TaskType fromJson(String value) {
    return TaskType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => TaskType.flashcard,
    );
  }
}

enum DifficultyBand {
  recognition('recognition'),
  repeat('repeat'),
  comprehension('comprehension'),
  output('output');

  const DifficultyBand(this.value);

  final String value;

  static DifficultyBand fromJson(String value) {
    return DifficultyBand.values.firstWhere(
      (band) => band.value == value,
      orElse: () => DifficultyBand.recognition,
    );
  }
}

enum ReviewTaskStatus {
  pending('pending'),
  inProgress('in_progress'),
  completed('completed');

  const ReviewTaskStatus(this.value);

  final String value;

  static ReviewTaskStatus fromJson(String value) {
    return ReviewTaskStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => ReviewTaskStatus.pending,
    );
  }
}

enum SpeakingAttemptStatus {
  queued('queued'),
  recordingUploaded('recording_uploaded'),
  transcribing('transcribing'),
  scored('scored'),
  failed('failed');

  const SpeakingAttemptStatus(this.value);

  final String value;

  static SpeakingAttemptStatus fromJson(String value) {
    return SpeakingAttemptStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => SpeakingAttemptStatus.queued,
    );
  }
}
