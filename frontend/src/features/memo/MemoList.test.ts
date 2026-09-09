import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  EXPANDED_STORAGE_KEY,
  loadExpandedIds,
  saveExpandedIds,
} from "./MemoList";

describe("MemoList expanded state persistence", () => {
  let store: Record<string, string> = {};

  beforeEach(() => {
    store = {};
    const mockStorage = {
      getItem: vi.fn((key: string) => store[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
      clear: vi.fn(() => {
        store = {};
      }),
      length: 0,
      key: vi.fn(),
    };

    vi.stubGlobal("window", {
      localStorage: mockStorage,
    });
    vi.stubGlobal("localStorage", mockStorage);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  test("loads empty set when nothing is in localStorage", () => {
    const ids = loadExpandedIds();
    expect(ids.size).toBe(0);
  });

  test("saves and reloads expanded ids", () => {
    saveExpandedIds(new Set([1, 42, 100]));
    const ids = loadExpandedIds();
    expect(ids.has(1)).toBe(true);
    expect(ids.has(42)).toBe(true);
    expect(ids.has(100)).toBe(true);
    expect(ids.size).toBe(3);
  });

  test("filters out non-numeric values gracefully", () => {
    localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify([1, "bad", null, 99]));
    const ids = loadExpandedIds();
    expect(ids.has(1)).toBe(true);
    expect(ids.has(99)).toBe(true);
    expect(ids.size).toBe(2);
  });

  test("handles corrupted JSON gracefully by returning empty set", () => {
    localStorage.setItem(EXPANDED_STORAGE_KEY, "{not valid json");
    const ids = loadExpandedIds();
    expect(ids.size).toBe(0);
  });

  test("handles localStorage errors gracefully", () => {
    vi.mocked(localStorage.getItem).mockImplementation(() => {
      throw new Error("SecurityError: Access is denied");
    });
    vi.mocked(localStorage.setItem).mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });

    expect(() => saveExpandedIds(new Set([1, 2]))).not.toThrow();
    expect(() => loadExpandedIds()).not.toThrow();
    expect(loadExpandedIds().size).toBe(0);
  });
});
