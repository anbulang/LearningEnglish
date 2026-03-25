# LearningEnglish Stitch Prompts

## Shared Design System Prompt
Use this block in every Stitch prompt.

```md
Design a mobile-first educational app for Chinese parents and young children learning English after live classes. The product turns printed English worksheets into digital review packs. The design should feel warm, gentle, and premium without looking like a generic school dashboard.

**DESIGN SYSTEM (REQUIRED):**
- Platform: Mobile app, mobile-first with clear tablet adaptation
- Theme: Light, family-friendly, calm editorial
- Background: Warm Linen (#FFF8F5)
- Surface: Soft Sheet (#FFF1E9) with Paper White (#FFFFFF) lifted cards
- Primary Accent: Coral Jam (#F28C6B) with Cocoa Coral (#98462A) for stronger CTA gradients
- Success Accent: Mint Leaf (#9DF3DF) with Forest Mint (#006B5C)
- Text Primary: Ink Cocoa (#251910)
- Text Secondary: Dust Brown (#55433D)
- Borders: Outline Variant (#DBC1B9)
- Typography: Plus Jakarta Sans for headings and labels, Be Vietnam Pro for body and Chinese UI copy
- Geometry: Very rounded cards, pill-shaped chips, tonal layering with whisper-soft shadows
- Atmosphere: Calm, child-friendly, parent-trustworthy, low-pressure learning companion
```

## Mobile Screen Prompts

### 1. Parent Home
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Top Header:** Warm greeting, active child switcher, subtle notification icon.
2. **Today Review Hero:** Large card showing today's next review action, estimated 10-minute session, and primary CTA.
3. **Recent Lessons:** Horizontal or vertical lesson cards with thumbnails, topic tags, and review status.
4. **Weekly Progress:** Soft progress card with learned words, completed sessions, and one weak-point hint.
5. **Quick Actions:** Upload worksheet, parent coaching, start review.
6. **Bottom Navigation:** 首页, 资料库, 复习, 报告, 我的.
```

### 2. Materials Library
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Page title and add/upload action.
2. **Search And Filter Row:** Search input, status chips, topic chips, date chip.
3. **Lesson Card List:** Each card shows thumbnail, lesson date, child name, topic, and parsing/review status.
4. **Floating Action:** Upload worksheet.
```

### 3. Scan And Upload
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Back button, page title, help icon.
2. **Camera Surface:** Large scan preview with page boundary hints.
3. **Capture Toolbar:** Capture, retake, auto-enhance, multi-page controls.
4. **Page Strip:** Captured page thumbnails in a horizontal tray.
5. **Primary CTA:** Complete upload and begin AI recognition.
```

### 4. AI Processing And Parent Review
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Status Hero:** Processing timeline or ready state.
2. **Topic Summary Card:** Lesson title, probable topic, teacher/date metadata.
3. **Editable Vocabulary Section:** Extracted words with confidence badges.
4. **Editable Sentence Section:** Sentence patterns and simple edit affordances.
5. **Primary CTA:** Confirm and generate review pack.
```

### 5. Lesson Detail
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Lesson Header:** Topic title, tags, date, teacher, review completion badge.
2. **Source Preview:** Worksheet/PDF preview card.
3. **Vocabulary Module:** Scrollable word chips or cards with audio shortcuts.
4. **Sentence Pattern Module:** Highlighted sentence cards.
5. **Review Pack Actions:** Word cards, listening practice, speaking practice, parent coaching.
```

### 6. Vocabulary Cards And Listening
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Progress Header:** Current card index and child-friendly progress.
2. **Large Word Card:** Word, phonics, Chinese hint, image area.
3. **Audio Controls:** Play, slow repeat, favorite.
4. **Navigation Controls:** Previous and next.
5. **Soft Footer:** Continue to practice game.
```

### 7. Practice Game Flow
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Prompt Header:** Very short instruction.
2. **Game Area:** Visual multiple choice or matching interaction.
3. **Feedback Strip:** Great job, try again, or almost right.
4. **Progress Footer:** Step count and next button.
```

### 8. AI Speaking Partner
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Speaking Header:** Session title and progress.
2. **AI Character Card:** Warm illustrated assistant asking one simple question.
3. **Prompt Panel:** One sentence prompt in large text.
4. **Recording Area:** Large microphone button, waveform, retry button.
5. **Response Result:** Transcript, encouragement, and improved answer hint.
```

### 9. Parent Coaching Mode
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Parent coaching title and target lesson reference.
2. **Current Step Card:** What the parent should say now.
3. **Hint Card:** Prompt if the child is stuck.
4. **Expansion Card:** Slightly better answer to model.
5. **Completion Footer:** Mark finished and move to next prompt.
```

### 10. Weekly Review And Report
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Week Summary Hero:** Week completion and review streak.
2. **Metric Cards:** Words reviewed, speaking attempts, completion rate.
3. **Weak Point Section:** Difficult words and sentence patterns.
4. **Recommended Next Steps:** Suggested tasks for the next 3 days.
5. **Primary CTA:** Start weekly review pack.
```

### 11. Multi-Child And Profile Management
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Profile and settings title.
2. **Child Switch Cards:** Multiple child cards with current selection state.
3. **Profile Detail Form:** Age, level, goals, lesson preferences.
4. **Settings Section:** Notifications, reminder times, parent mode options.
```

## Tablet Variant Prompts
Use these after generating the mobile screens, preserving all content but changing layout for larger canvases.

### Tablet Home Variant
`Convert the parent home screen into a tablet layout with a left navigation rail, a central dashboard feed, and a right-side panel for today summary and quick actions. Keep the same warm design system and all existing content.`

### Tablet Materials Variant
`Convert the materials library into a tablet master-detail layout with the searchable lesson list on the left and the selected lesson preview plus metadata on the right.`

### Tablet Lesson Detail Variant
`Convert the lesson detail screen into a tablet split view with the worksheet preview on the left and vocabulary, sentence patterns, and review actions on the right.`

### Tablet Speaking Variant
`Convert the AI speaking partner screen into a tablet layout with the speaking stage on the left and transcript, encouragement, and progress details on the right.`

### Tablet Report Variant
`Convert the weekly review and report screen into a tablet dashboard with a metric card grid, persistent weak-point panel, and recommended actions column.`
