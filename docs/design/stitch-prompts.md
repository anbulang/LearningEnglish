# LearningEnglish Stitch Prompts

## Shared Design System Prompt
Use this block in every Stitch prompt.

```md
Design a mobile-first educational app for Chinese parents and young children learning English after live classes. The product turns printed English worksheets into digital review packs. The interface must feel like a warm picture-book learning companion instead of a generic school dashboard.

**DESIGN SYSTEM (REQUIRED):**
- Platform: Mobile app, mobile-first with clear tablet adaptation
- Theme: Light, family-friendly, illustrated, premium, calm
- Background: Warm Linen (#FFF8F5)
- Surface: Soft Sheet (#FFF1E9) with Paper White (#FFFFFF) lifted cards
- Primary Accent: Coral Jam (#F28C6B) with Cocoa Coral (#98462A)
- Success Accent: Mint Leaf (#9DF3DF) with Forest Mint (#006B5C)
- Reward Accent: Butter Yellow (#FFD86A)
- Audio Accent: Sky Blue (#BFE7FF)
- Text Primary: Ink Cocoa (#251910)
- Text Secondary: Dust Brown (#55433D)
- Borders: Outline Variant (#DBC1B9), only when necessary
- Typography: Plus Jakarta Sans for headings and labels, Be Vietnam Pro for body and Chinese UI copy
- Geometry: Very rounded cards, sticker-like badges, layered paper-cut shapes, tonal layering with whisper-soft shadows
- Atmosphere: Warm educational picture-book, parent-trustworthy, softly playful, tactile, scrapbook-like

**MANDATORY VISUAL RULES:**
- The UI must contain AI-illustrated scenes, sticker-like accent elements, and soft educational motifs on every key screen.
- Avoid text-only dashboards and generic SaaS cards.
- Use large hero illustrations, playful but premium composition, and child-friendly visual anchors.
- Keep parents’ trust with readable typography and calm layout density.
```

## Mobile Screen Prompts

### 1. Parent Home
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Top Header:** Warm greeting, active child switcher, subtle notification icon.
2. **Hero:** Large AI-illustrated parent-child study scene.
3. **Today Review Card:** Estimated 10-minute session, encouragement message, reward badge, and primary CTA.
4. **Recent Lessons:** Lesson cards with illustrated topic thumbnails.
5. **Weekly Progress:** Soft progress card plus one weak-point reminder.
6. **Quick Actions:** Upload worksheet, parent coaching, start review.
7. **Bottom Navigation:** 首页, 资料库, 复习, 报告, 我的.

**IMAGE / ILLUSTRATION ROLE:**
- The hero illustration is the main memory anchor.
- Recent lesson cards must feel like mini cover cards, not plain metadata rows.
```

### 2. Materials Library
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Page title and add/upload action.
2. **Illustrated Header Strip:** A soft paper-collage header above search and filters.
3. **Search And Filter Row:** Search input, status chips, topic chips, date chip.
4. **Lesson Card List:** Each card shows cover art, lesson date, child name, topic, and parsing/review status.
5. **Floating Action:** Upload worksheet.

**IMAGE / ILLUSTRATION ROLE:**
- Each lesson card needs thematic image presence.
- The header strip should visually set a warm library/discovery mood.
```

### 3. Scan And Upload
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Back button, page title, help icon.
2. **Camera Surface:** Large scan preview with page boundary hints.
3. **Illustrated Transformation Layer:** A visual metaphor that worksheets become review cards.
4. **Capture Toolbar:** Capture, retake, auto-enhance, multi-page controls.
5. **Page Strip:** Captured page thumbnails in a horizontal tray.
6. **Primary CTA:** Complete upload and begin AI recognition.

**IMAGE / ILLUSTRATION ROLE:**
- Empty or pre-capture state should include a friendly illustration around the scan stage.
- The page must feel inviting rather than tool-like.
```

### 4. AI Processing And Parent Review
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Process Hero:** A visual journey from worksheet to AI understanding to review pack.
2. **Topic Summary Card:** Lesson title, probable topic, teacher/date metadata.
3. **Editable Vocabulary Section:** Extracted words with confidence stickers.
4. **Editable Sentence Section:** Sentence patterns and simple edit affordances.
5. **Primary CTA:** Confirm and generate review pack.

**IMAGE / ILLUSTRATION ROLE:**
- The top area must clearly visualize the AI transformation process.
- Source preview and extracted content should feel visually distinct and layered.
```

### 5. Lesson Detail
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Lesson Hero:** Topic illustration, tags, date, teacher, review completion badge.
2. **Source Preview:** Worksheet/PDF preview card.
3. **Vocabulary Module:** Rich learning-pack cards with audio shortcuts.
4. **Sentence Pattern Module:** Highlighted sentence cards.
5. **Review Pack Actions:** Word cards, listening practice, speaking practice, parent coaching.

**IMAGE / ILLUSTRATION ROLE:**
- The lesson hero must feel like a cover image for the learning pack.
- Vocabulary and sentence modules should look like colorful pack pieces, not plain lists.
```

### 6. Vocabulary Cards And Listening
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Progress Header:** Current card index and child-friendly progress.
2. **Large Word Card:** Word, phonics, Chinese hint, and big illustrated image area.
3. **Audio Controls:** Play, slow repeat, favorite.
4. **Navigation Controls:** Previous and next.
5. **Soft Footer:** Continue to practice game.

**IMAGE / ILLUSTRATION ROLE:**
- The illustration must dominate the card and make the word memorable.
- Use sky blue accents to frame audio/listening interactions.
```

### 7. Practice Game Flow
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Prompt Header:** Very short instruction.
2. **Game Area:** Visual multiple choice or matching interaction.
3. **Feedback Strip:** Great job, try again, or almost right.
4. **Progress Footer:** Step count and next button.

**IMAGE / ILLUSTRATION ROLE:**
- Answer options should feel visual and tactile.
- Feedback can use a small celebratory badge or sticker accent.
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

**IMAGE / ILLUSTRATION ROLE:**
- The AI companion must be a memorable illustrated guide.
- Use sky blue accents for speaking and audio energy.
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

**IMAGE / ILLUSTRATION ROLE:**
- Add a warm parent-child guidance illustration or coaching vignette.
- Coaching cards should feel reassuring rather than instructional-heavy.
```

### 10. Weekly Review And Report
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Week Summary Hero:** Week completion, review streak, and visual growth metaphor.
2. **Metric Cards:** Words reviewed, speaking attempts, completion rate.
3. **Weak Point Section:** Difficult words and sentence patterns.
4. **Recommended Next Steps:** Suggested tasks for the next 3 days.
5. **Primary CTA:** Start weekly review pack.

**IMAGE / ILLUSTRATION ROLE:**
- Use growth-oriented illustration, reward stickers, or family progress imagery.
- Metrics should not feel like a corporate dashboard.
```

### 11. Multi-Child And Profile Management
```md
[Shared design system prompt]

**PAGE STRUCTURE:**
1. **Header:** Profile and settings title.
2. **Child Switch Cards:** Multiple child cards with current selection state.
3. **Profile Detail Form:** Age, level, goals, lesson preferences.
4. **Settings Section:** Notifications, reminder times, parent mode options.

**IMAGE / ILLUSTRATION ROLE:**
- Use family-oriented profile illustrations or avatar cards.
- The page should feel soft and personal, not settings-heavy.
```

## Tablet Variant Prompts
Use these after generating the mobile screens, preserving all content but changing layout for larger canvases.

### Tablet Home Variant
`Convert the parent home screen into a tablet layout with a left navigation rail, a central scrapbook-style dashboard feed, and a right-side panel anchored by a large family-learning illustration. Keep the same warm illustrated design system and all existing content. The right panel must not feel like stacked generic white cards.`

### Tablet Materials Variant
`Convert the materials library into a tablet master-detail layout with the searchable lesson list on the left and a stronger illustrated lesson preview on the right. Use cover-art-like lesson imagery and layered panels instead of generic list-detail cards.`

### Tablet Lesson Detail Variant
`Convert the lesson detail screen into a tablet split view with the worksheet preview on the left and a rich illustrated learning-pack composition on the right. The right side must use stronger visual hierarchy and not feel like stacked white cards.`

### Tablet Speaking Variant
`Convert the AI speaking partner screen into a tablet layout with the speaking stage and friendly illustrated companion on the left and transcript, encouragement, and progress details on the right. Use sky blue accents and keep the right panel calm but visually anchored.`

### Tablet Report Variant
`Convert the weekly review and report screen into a tablet dashboard with grouped metric panels, a persistent weak-point area, and a large growth illustration that makes the data feel encouraging rather than clinical.`
