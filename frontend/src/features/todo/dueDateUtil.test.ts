import { describe, expect, it } from "vitest";

import { getDueDateStatus } from "./dueDateUtil";

describe("getDueDateStatus", () => {
  const refDate = new Date(2026, 8, 8); // 2026-09-08

  it("returns none when dueDate is null or empty", () => {
    expect(getDueDateStatus(null, refDate)).toBe("none");
    expect(getDueDateStatus("", refDate)).toBe("none");
  });

  it("returns overdue when dueDate is in the past", () => {
    expect(getDueDateStatus("2026-09-07", refDate)).toBe("overdue");
    expect(getDueDateStatus("2025-12-31", refDate)).toBe("overdue");
  });

  it("returns today when dueDate is today", () => {
    expect(getDueDateStatus("2026-09-08", refDate)).toBe("today");
  });

  it("returns future when dueDate is in the future", () => {
    expect(getDueDateStatus("2026-09-09", refDate)).toBe("future");
    expect(getDueDateStatus("2026-10-01", refDate)).toBe("future");
  });
});
