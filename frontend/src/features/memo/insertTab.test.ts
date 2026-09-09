import { describe, expect, it, vi, afterEach } from "vitest";

import { insertTab } from "./insertTab";

describe("insertTab", () => {
  const originalDocument = (globalThis as any).document;

  afterEach(() => {
    (globalThis as any).document = originalDocument;
  });

  function createFakeTextarea(initial: string, start: number, end: number) {
    return {
      value: initial,
      selectionStart: start,
      selectionEnd: end,
    } as unknown as HTMLTextAreaElement;
  }

  it("uses document.execCommand('insertText', false, '\\t') when available", () => {
    const textarea = createFakeTextarea("hello", 5, 5);
    const execMock = vi.fn().mockReturnValue(true);
    (globalThis as any).document = { execCommand: execMock };

    const fallback = vi.fn();
    insertTab(textarea, fallback);
    expect(execMock).toHaveBeenCalledWith("insertText", false, "\t");
    expect(fallback).not.toHaveBeenCalled();
  });

  it("falls back to fallbackSetState and replaces selection when execCommand returns false", () => {
    const textarea = createFakeTextarea("hello world", 6, 11);
    const execMock = vi.fn().mockReturnValue(false);
    (globalThis as any).document = { execCommand: execMock };

    const fallback = vi.fn();
    insertTab(textarea, fallback);
    expect(execMock).toHaveBeenCalledWith("insertText", false, "\t");
    expect(fallback).toHaveBeenCalledWith("hello \t");
  });

  it("falls back to fallbackSetState when execCommand throws an error", () => {
    const textarea = createFakeTextarea("abc", 1, 1);
    const execMock = vi.fn().mockImplementation(() => {
      throw new Error("execCommand not supported");
    });
    (globalThis as any).document = { execCommand: execMock };

    const fallback = vi.fn();
    insertTab(textarea, fallback);
    expect(fallback).toHaveBeenCalledWith("a\tbc");
  });
});
