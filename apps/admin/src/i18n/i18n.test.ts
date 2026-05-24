import { describe, expect, it } from "vitest";
import { createTranslator } from "./i18n";

describe("i18n", () => {
  it("translates navigation labels", () => {
    expect(createTranslator("zh")("nav.commandCenter")).toBe("指挥台");
    expect(createTranslator("en")("nav.commandCenter")).toBe("Command Center");
  });

  it("keeps code tokens outside translation", () => {
    expect(createTranslator("zh")("code.aiProvider")).toBe("AI_PROVIDER");
    expect(createTranslator("en")("code.aiProvider")).toBe("AI_PROVIDER");
  });
});
