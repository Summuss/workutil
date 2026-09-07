import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";

import { MemoMarkdown } from "./MemoMarkdown";

/**
 * The one automated test on the frontend, and a deliberate exception to
 * "前端 UI 不写自动化测试" (spec Testing Decisions).
 *
 * Memo bodies are mostly pasted from web pages, Slack and error screens, and
 * this page can call a `127.0.0.1` backend that later gains arbitrary Python
 * execution (F4). Rendering raw HTML would join those two ends. Nothing else
 * enforces that — react-markdown escapes HTML only while no one adds
 * `rehype-raw`, and that is a one-line change away.
 */
function render(markdown: string): string {
  return renderToStaticMarkup(<MemoMarkdown content={markdown} />);
}

describe("a memo body pasted in from outside", () => {
  test("shows its HTML tags as text instead of running them", () => {
    const html = render('<script>alert("xss")</script><p>原生标签</p>');

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<p>原生标签</p>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("原生标签");
  });

  test("does not run an inline event handler", () => {
    const html = render('<img src="x" onerror="evil()">');

    // No element reaches the DOM at all: the tag is text, quotes and all.
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img src=&quot;x&quot; onerror=&quot;evil()&quot;&gt;");
  });

  test("strips a javascript: link", () => {
    const html = render("[click me](javascript:alert(1))");

    expect(html).not.toContain("javascript:");
    expect(html).toContain("click me");
  });

  test("still renders markdown, with code highlighted", () => {
    const html = render('```python\nraise ValueError("boom")\n```');

    expect(html).toContain("<pre>");
    expect(html).toContain("language-python");
    expect(html).toContain("hljs-keyword");
  });
});
