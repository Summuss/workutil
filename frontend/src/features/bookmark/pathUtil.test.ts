import { describe, expect, it } from "vitest";

import { extractNameFromPath } from "./pathUtil";

describe("extractNameFromPath", () => {
  it("extracts filename from Windows path", () => {
    expect(extractNameFromPath("C:\\Users\\admin\\config.yml")).toBe("config.yml");
  });

  it("extracts filename from quoted Windows path", () => {
    expect(extractNameFromPath('"C:\\Users\\admin\\My Documents\\test.docx"')).toBe(
      "test.docx",
    );
  });

  it("extracts folder name from path with trailing backslash", () => {
    expect(extractNameFromPath("D:\\Projects\\workutil\\")).toBe("workutil");
  });

  it("extracts filename from POSIX path", () => {
    expect(extractNameFromPath("/home/summus/Code/summus-workutil/main.py")).toBe(
      "main.py",
    );
  });

  it("extracts directory name from POSIX path with trailing slash", () => {
    expect(extractNameFromPath("/var/log/nginx/")).toBe("nginx");
  });

  it("handles empty or whitespace path", () => {
    expect(extractNameFromPath("   ")).toBe("");
  });
});
