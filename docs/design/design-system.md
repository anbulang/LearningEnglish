# LearningEnglish Design System

## Brand Direction
Warm, family-friendly, and editorial, but now visibly more alive. The UI should feel like a premium after-class learning scrapbook assembled from illustrated lesson moments, paper layers, and gentle rewards. It must stay safe and readable for parents while giving children clearer emotional cues and visual anchors.

## Visual Theme
- Style: warm learning picture-book
- Density: calm and breathable
- Mood: encouraging, handcrafted, affectionate, premium
- Theme priority: light mode first
- Playfulness level: medium, never noisy

## Core Visual Language
- Large AI-illustrated scenes on key screens
- Sticker-like accent labels and badges
- Paper-cut collage shapes, soft waves, stars, and cloud motifs
- Tonal layering and soft diffused shadows instead of hard card grids
- Image-led hierarchy instead of text-only dashboards

## Color Palette
- `Warm Linen` `#FFF8F5`: main background and base learning canvas
- `Soft Sheet` `#FFF1E9`: grouped sections and soft framing
- `Paper White` `#FFFFFF`: elevated cards and reading surfaces
- `Coral Jam` `#F28C6B`: primary actions and active highlights
- `Cocoa Coral` `#98462A`: stronger CTA anchor and gradient depth
- `Mint Leaf` `#9DF3DF`: supportive progress and positive feedback
- `Forest Mint` `#006B5C`: high-contrast positive text or accent
- `Butter Yellow` `#FFD86A`: rewards, badges, cheerful highlights
- `Sky Blue` `#BFE7FF`: listening, speaking, and audio modules
- `Ink Cocoa` `#251910`: primary text
- `Dust Brown` `#55433D`: secondary text
- `Outline Variant` `#DBC1B9`: soft fallback borders only when needed

## Typography
- Display and navigation font: `Plus Jakarta Sans`
- Body and Chinese UI font: `Be Vietnam Pro`
- Heading tone: editorial, friendly, premium
- Body tone: stable, highly readable, low-fatigue
- Hero headings can be larger and looser than before, but never whimsical to the point of losing trust

## Type Hierarchy
- Page hero title: 30-36 / 36-42, semibold
- Page title: 28 / 32, semibold
- Section title: 20 / 24, semibold
- Card title: 16 / 20, semibold
- Body: 14 / 20, regular
- Helper text: 12 / 16, medium

## Shape Language
- Cards: softly rounded 20px+ corners with occasional layered overlap
- Buttons: pill-shaped or very rounded for primary actions
- Chips and badges: sticker-like pills with friendlier emphasis
- Inputs: 16px corners with generous internal padding
- Hero media: organic framed surfaces rather than sharp rectangles

## Elevation
- Base surfaces stay close to the background
- Depth comes first from tonal layering, then from whisper-soft warm shadows
- Avoid hard divider lines and generic dashboard card grids
- Important cards may look like stacked paper sheets or soft scrapbook pieces

## Image Rules
- Home, upload, lesson detail, and weekly report must include a major illustration or scene
- Materials cards should include topic imagery or lesson cover thumbnails
- Vocabulary and speaking flows should include child-friendly illustrated anchors
- Tablet side panels must include a visual support element, not just stacked white cards

## Iconography
- Rounded line icons with simple silhouettes
- Filled variants may be used for celebration and active states
- Visual icons should support, not replace, the new illustration anchors

## Motion
- Short transitions: 180-220ms
- Use scale and fade for encouragement moments
- Keep motion gentle and warm, not arcade-like
- Reward moments can feel slightly more vivid than the first design pass

## Layout Tokens
- Base spacing unit: 8
- Card internal padding: 16 on phone, 20-24 on tablet
- Screen margins: 16 on phone, 24-32 on tablet
- Section gap: 16 on phone, 24 on tablet

## Responsive Principles
- Phone prioritizes one primary illustrated moment plus a clean vertical flow.
- Tablet keeps rail and split-pane patterns, but the right-side content must have clearer hierarchy and at least one visual anchor.
- The same semantic modules must exist on both device classes even if their composition changes.

## Accessibility Rules
- Minimum tap size: 48x48
- Parent-facing text remains readable at arm's length
- Important states use color plus text/icon treatment
- Child-facing screens must avoid dense instruction blocks
- Playfulness must never reduce clarity or contrast
