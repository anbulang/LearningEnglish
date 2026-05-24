import type { Language } from "../domain/types";
import { messages, type MessageKey } from "./messages";

export function createTranslator(language: Language) {
  return function translate(key: MessageKey): string {
    return messages[language][key] ?? messages.en[key] ?? key;
  };
}
