import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  STORAGE_KEY,
  detectLanguage,
  getLanguage,
  setLanguage,
  t,
} from "./index";
import ja from "./ja.json";
import zh from "./zh.json";

describe("i18n key alignment", () => {
  it("zh.json and ja.json have identical key sets", () => {
    const zhKeys = Object.keys(zh).sort();
    const jaKeys = Object.keys(ja).sort();

    const missingInJa = zhKeys.filter((k) => !(k in ja));
    const missingInZh = jaKeys.filter((k) => !(k in zh));

    expect(
      missingInJa,
      `Keys in zh.json but missing in ja.json: ${missingInJa.join(", ")}`,
    ).toEqual([]);
    expect(
      missingInZh,
      `Keys in ja.json but missing in zh.json: ${missingInZh.join(", ")}`,
    ).toEqual([]);
    expect(zhKeys).toEqual(jaKeys);
  });
});

describe("t() translation function", () => {
  beforeEach(() => {
    setLanguage("zh");
  });

  it("returns translation for existing key in current language", () => {
    setLanguage("zh");
    expect(t("nav.memo")).toBe("Memo");
    setLanguage("ja");
    expect(t("nav.memo")).toBe("メモ");
  });

  it("renders bare key with brackets when translation is missing without fallback", () => {
    expect(t("nonexistent.dummy.key")).toBe("[nonexistent.dummy.key]");
  });
});

describe("language detection and persistence", () => {
  let mockStorage: Record<string, string> = {};
  const originalWindow = globalThis.window;
  const originalDocument = globalThis.document;
  const originalNavigator = globalThis.navigator;

  beforeEach(() => {
    mockStorage = {};
    const storageMock = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, value: string) => {
        mockStorage[key] = value;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
      clear: () => {
        mockStorage = {};
      },
      length: 0,
      key: () => null,
    };

    const docMock = {
      documentElement: { lang: "zh" },
    };

    const navMock = {
      language: "en-US",
    };

    const winMock = {
      localStorage: storageMock,
    };

    Object.defineProperty(globalThis, "window", {
      value: winMock,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "localStorage", {
      value: storageMock,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "document", {
      value: docMock,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "navigator", {
      value: navMock,
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, "window", {
      value: originalWindow,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "document", {
      value: originalDocument,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "navigator", {
      value: originalNavigator,
      configurable: true,
      writable: true,
    });
  });

  it("defaults to zh when navigator.language is unrecognized", () => {
    (globalThis.navigator as any).language = "en-US";
    expect(detectLanguage()).toBe("zh");
  });

  it("detects ja when navigator.language starts with ja", () => {
    (globalThis.navigator as any).language = "ja-JP";
    expect(detectLanguage()).toBe("ja");
  });

  it("detects zh when navigator.language starts with zh", () => {
    (globalThis.navigator as any).language = "zh-TW";
    expect(detectLanguage()).toBe("zh");
  });

  it("prioritizes localStorage over navigator.language", () => {
    (globalThis.navigator as any).language = "zh-CN";
    mockStorage[STORAGE_KEY] = "ja";
    expect(detectLanguage()).toBe("ja");
  });

  it("updates activeLanguage and document.documentElement.lang on setLanguage", () => {
    setLanguage("ja");
    expect(getLanguage()).toBe("ja");
    expect(document.documentElement.lang).toBe("ja");
    expect(mockStorage[STORAGE_KEY]).toBe("ja");

    setLanguage("zh");
    expect(getLanguage()).toBe("zh");
    expect(document.documentElement.lang).toBe("zh");
    expect(mockStorage[STORAGE_KEY]).toBe("zh");
  });
});
