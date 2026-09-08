import { describe, expect, it } from "vitest";

import { firstLine } from "./firstLine";

describe("firstLine", () => {
  it("extracts the first non-empty line", () => {
    expect(firstLine("Hello world\nSecond line")).toBe("Hello world");
  });

  it("skips leading empty lines", () => {
    expect(firstLine("\n\n  Third line  \nFourth line")).toBe("Third line");
  });

  it("returns empty string for empty content", () => {
    expect(firstLine("")).toBe("");
    expect(firstLine("   \n\n  ")).toBe("");
  });
});
