# GPT-image-2 Visual Asset Pack

This document freezes the first static illustration pack for the MVP UI. The app should render all text in Flutter; generated images only carry scene, mood, topic, and state.

## Asset Strategy

- Use warm picture-book illustrations with paper collage texture, rounded sticker accents, soft shadows, and calm parent-friendly composition.
- Avoid embedded Chinese or English text inside images.
- Use opaque `png` or `webp`; do not require transparent backgrounds.
- Keep current file names stable so generated GPT-image-2 assets can replace local placeholder assets without code changes.

## Shared Prompt

Create a warm parent-child English learning app illustration in a premium children's picture-book style. Use soft paper collage texture, rounded sticker accents, warm linen background, coral, mint, butter yellow, and sky blue highlights. Keep the composition calm, trustworthy, and friendly for parents. Do not include any readable text, logos, UI chrome, watermarks, or photorealistic 3D rendering.

## Required Files

| Path | Visual Intent |
| --- | --- |
| `assets/images/heroes/login_parent_child_pack.png` | Parent and child turning paper worksheets into an English lesson pack. |
| `assets/images/heroes/home_study_desk.png` | Parent-child 10-minute study desk with cards, headphones, and gentle reward elements. |
| `assets/images/heroes/upload_worksheet_to_pack.png` | Worksheet pages flowing into word cards and a review pack. |
| `assets/images/heroes/ai_processing.png` | Friendly AI helper reading a worksheet and extracting cards. |
| `assets/images/heroes/ai_ready.png` | Finished review pack with vocabulary cards and a parent confirmation mood. |
| `assets/images/heroes/ai_retry.png` | Gentle retry state with worksheet, magnifier, and repair stickers. |
| `assets/images/heroes/lesson_pack.png` | Generic lesson pack hero for course detail. |
| `assets/images/heroes/weekly_growth.png` | Weekly growth garden with badges and completed review cards. |
| `assets/images/heroes/speaking_partner.png` | Child speaking with headphones and a friendly voice bubble motif. |
| `assets/images/heroes/parent_coaching.png` | Parent coaching child with prompt cards at a small table. |
| `assets/images/topics/animals.png` | Animal topic cover with cat, dog, bird. |
| `assets/images/topics/numbers.png` | Number topic cover with counting blocks and dots. |
| `assets/images/topics/phonics.png` | Phonics topic cover with letters, mouth sound marks, and cards. |
| `assets/images/topics/colors.png` | Color topic cover with swatches and playful brushes. |
| `assets/images/topics/fruits.png` | Fruit topic cover with apple and banana cards. |
| `assets/images/topics/family.png` | Family members topic cover with warm home scene. |
| `assets/images/topics/dialogue.png` | Daily dialogue topic cover with two speech bubbles and cards. |
| `assets/images/states/empty.png` | Empty state with open study table and waiting worksheet. |
| `assets/images/states/error.png` | Recoverable error state with soft warning sticker and retry mood. |
| `assets/images/states/success.png` | Completed state with badge, stars, and finished cards. |
| `assets/images/states/network.png` | Network issue state with cloud and reconnect motif. |
| `assets/images/vocabulary/cat.png` | Cat vocabulary card, no text. |
| `assets/images/vocabulary/dog.png` | Dog vocabulary card, no text. |
| `assets/images/vocabulary/bird.png` | Bird vocabulary card, no text. |
| `assets/images/vocabulary/apple.png` | Apple vocabulary card, no text. |
| `assets/images/vocabulary/banana.png` | Banana vocabulary card, no text. |
| `assets/images/vocabulary/red.png` | Red color vocabulary card, no text. |
| `assets/images/vocabulary/blue.png` | Blue color vocabulary card, no text. |

## Implementation Notes

- Flutter registers the folders in `apps/mobile/pubspec.yaml`.
- `AppIllustrations` owns the stable paths and topic/word mappings.
- `IllustratedHeroCard`, `LessonCoverThumbnail`, and `StatePanel` render `assetPath` first and fall back to Material icons if assets are missing.
- Current checked-in images are local placeholder illustrations because the build environment did not include `OPENAI_API_KEY`; they are intentionally named as final replacement targets.
