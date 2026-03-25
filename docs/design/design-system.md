# LearningEnglish Design System

## Brand Direction
Warm, calm, and family-friendly with an editorial feel. The UI should feel more like a guided study companion than a testing platform. It must be soft enough for children and trustworthy enough for parents.

## Visual Theme
- Style: warm educational companion
- Density: light and breathable
- Mood: encouraging, reassuring, structured
- Theme priority: light mode first

## Color Palette
- `Warm Linen` `#FFF8F5`: app background and base learning canvas
- `Soft Sheet` `#FFF1E9`: grouped sections and soft content framing
- `Paper White` `#FFFFFF`: elevated cards and flashcards
- `Coral Jam` `#F28C6B`: primary actions and active highlights
- `Cocoa Coral` `#98462A`: stronger CTA anchor and gradient depth
- `Mint Leaf` `#9DF3DF`: success, progress, and supportive feedback
- `Forest Mint` `#006B5C`: high-contrast positive text or accent
- `Ink Cocoa` `#251910`: primary text
- `Dust Brown` `#55433D`: secondary text
- `Outline Variant` `#DBC1B9`: soft borders and ghost separators

## Typography
- Display and navigation font: `Plus Jakarta Sans`
- Body and Chinese UI font: `Be Vietnam Pro`
- Heading tone: editorial, friendly, slightly bold
- Body tone: highly readable, stable, low-fatigue

## Type Hierarchy
- Page title: 28/32, semibold
- Section title: 20/24, semibold
- Card title: 16/20, semibold
- Body: 14/20, regular
- Helper text: 12/16, medium

## Shape Language
- Cards: softly rounded 20px corners or more
- Buttons: pill-shaped or very rounded for primary actions
- Chips and tags: pill-shaped
- Inputs: 16px corners with strong internal padding

## Elevation
- Base surfaces stay close to the background
- Cards use tonal layering first, whisper-soft warm shadows second
- Avoid hard 1px separators unless required for accessibility
- Primary CTA uses slightly stronger visual lift than passive content

## Iconography
- Rounded line icons with simple silhouettes
- Active states may use filled icon variants
- Icons should remain readable for young children at a distance

## Motion
- Short transitions: 180-220ms
- Use scale and fade for encouragement moments
- Avoid noisy looping motion
- Feedback moments should feel gentle, not arcade-like

## Layout Tokens
- Base spacing unit: 8
- Card internal padding: 16 on phone, 20-24 on tablet
- Screen margins: 16 on phone, 24-32 on tablet
- Section gap: 16 on phone, 24 on tablet

## Responsive Principles
- Phone prioritizes single focus with strong vertical flow.
- Tablet prioritizes simultaneous visibility of list, source material, and generated content.
- Tablet patterns should use navigation rail plus split panes for source-detail and list-detail relationships.
- The same semantic components must exist on both device classes even if layout differs.

## Accessibility Rules
- Minimum tap size: 48x48
- Text and controls should remain legible for parents at arm's length
- Important learning actions use both color and icon/text to communicate state
- Child-facing flows must avoid dense text blocks and low-contrast instructional text
