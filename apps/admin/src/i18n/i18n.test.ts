import { describe, expect, it } from "vitest";
import { createTranslator } from "./i18n";
import { messages } from "./messages";

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
});
