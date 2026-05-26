import { describe, expect, it } from "vitest";
import { createTranslator, translateMessage, type MessageCatalog } from "./i18n";
import { messages, type MessageKey } from "./messages";

describe("i18n", () => {
  it("translates navigation labels", () => {
    expect(createTranslator("zh")("nav.commandCenter")).toBe("指挥台");
    expect(createTranslator("en")("nav.commandCenter")).toBe("Command Center");
  });

  it("keeps code tokens outside translation", () => {
    expect(createTranslator("zh")("code.aiProvider")).toBe("AI_PROVIDER");
    expect(createTranslator("en")("code.aiProvider")).toBe("AI_PROVIDER");
  });

  it("keeps Chinese and English message keys in parity", () => {
    expect(Object.keys(messages.en).sort()).toEqual(Object.keys(messages.zh).sort());
  });

  it("falls back from missing localized values to English", () => {
    const catalog: MessageCatalog = {
      zh: {},
      en: {
        "nav.commandCenter": "Command Center"
      }
    };

    expect(translateMessage("zh", "nav.commandCenter", catalog)).toBe("Command Center");
  });

  it("falls back to the key when all catalog values are missing", () => {
    const catalog: MessageCatalog = {
      zh: {},
      en: {}
    };
    const key: MessageKey = "nav.commandCenter";

    expect(translateMessage("zh", key, catalog)).toBe(key);
  });
});
