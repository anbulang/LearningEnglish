import type { Language } from "../domain/types";
import { messages, type MessageKey } from "./messages";

export type MessageCatalog = Readonly<Record<Language, Partial<Record<MessageKey, string>>>>;

export function translateMessage(language: Language, key: MessageKey, catalog: MessageCatalog = messages): string {
  return catalog[language][key] ?? catalog.en[key] ?? key;
}

export function createTranslator(language: Language) {
  return function translate(key: MessageKey): string {
    return translateMessage(language, key);
  };
}

/**
 * Pick the matching half of a per-page bilingual copy pack. Pages keep their
 * screen-specific copy in a local `{ zh: {...}, en: {...} }` object and call
 * `localize(language, copy)` to get the active language's strings.
 */
export function localize<T>(language: Language, pack: Record<Language, T>): T {
  return pack[language];
}
