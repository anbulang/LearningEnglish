# LearningEnglish Screen Specification

## Screen Inventory
This specification covers 11 mobile-first screens plus 5 tablet variants.

## 1. Parent Home
- Goal: show today's next action and reduce navigation friction
- Main sections:
  - greeting and active child switcher
  - today's review tasks
  - recent lessons
  - weekly progress card
  - quick actions for upload, review, parent coaching
- Empty state: explain how to upload the first worksheet
- Tablet variant: left navigation rail, center dashboard feed, right summary panel

## 2. Materials Library
- Goal: browse, search, and filter lesson materials
- Main sections:
  - search bar
  - filter chips for topic, status, date
  - lesson cards with thumbnail, date, tags, review status
- Empty state: no lessons yet, CTA to upload
- Tablet variant: list on left, selected lesson preview on right

## 3. Scan And Upload
- Goal: capture one or more worksheet pages
- Main sections:
  - camera/scan preview
  - recent captured pages strip
  - auto-enhance toggle, add page, complete upload actions
- Failure state: blurry scan warning, retry capture
- Tablet layout: left preview, right capture controls and page list

## 4. AI Processing And Parent Review
- Goal: make OCR/parsing transparent and editable
- Main sections:
  - processing timeline or ready status
  - extracted title/topic
  - editable words and sentence sections
  - confidence warnings for low-quality extraction
- Empty state: waiting for OCR
- Tablet layout: source document left, extracted structure right

## 5. Lesson Detail
- Goal: connect original worksheet, extracted knowledge, and generated review pack
- Main sections:
  - lesson hero with topic and teacher/date metadata
  - source document preview
  - vocabulary strip
  - sentence patterns
  - review pack entry points
- Tablet variant: source document pane + knowledge/review detail pane

## 6. Vocabulary Cards And Listening
- Goal: lightweight review with image, audio, and meaning support
- Main sections:
  - progress header
  - large word card
  - illustration/image slot
  - audio and repeat controls
  - next/previous actions
- Tablet layout: card center, queue/progress sidebar

## 7. Practice Game Flow
- Goal: keep post-class repetition playful but structured
- Main sections:
  - short prompt
  - question surface for choice/matching/order
  - immediate feedback banner
  - simple progress tracker
- Variants:
  - listen and choose
  - image and word matching
  - sentence fill-in

## 8. AI Speaking Partner
- Goal: let the child answer short spoken prompts with encouragement
- Main sections:
  - animated AI guide
  - one prompt at a time
  - record button
  - transcript/result card
  - encouragement and retry CTA
- Failure state: microphone or network issue
- Tablet variant: prompt stage left, transcript and scoring right

## 9. Parent Coaching Mode
- Goal: help the parent ask the right questions even without teaching expertise
- Main sections:
  - step-by-step coaching script
  - what to say now
  - hint if the child is stuck
  - encourage/expand sentence suggestions
- Tablet layout: script steps left, child context and target language right

## 10. Weekly Review And Report
- Goal: show progress, weak points, and next practice plan
- Main sections:
  - week summary hero
  - completed tasks metrics
  - weak words and sentence patterns
  - recommended next review tasks
  - weekly review pack CTA
- Tablet variant: metric cards grid with persistent weak-point panel

## 11. Multi-Child And Profile Management
- Goal: manage children, levels, goals, and settings
- Main sections:
  - child switch cards
  - child profile details
  - level and goal settings
  - device, notifications, and parent preferences

## Shared States
- Loading: skeleton cards and clear processing labels
- Empty: illustration + one primary CTA
- Error: calm explanation + retry path
- Success: small celebratory feedback without confetti overload

## Breakpoint Rules
- `<600dp`: bottom navigation, full-screen task flows
- `600-840dp`: navigation bar or drawer, larger cards, more horizontal grouping
- `>840dp`: navigation rail + detail pane, denser but still breathable dashboard and report layouts
