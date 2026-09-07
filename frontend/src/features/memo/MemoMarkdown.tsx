import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";

interface MemoMarkdownProps {
  content: string;
}

/**
 * Renders memo markdown safely:
 * - Code blocks display in monospace font with syntax highlighting.
 * - Raw HTML tags and scripts are escaped to plain text, never executed by the browser.
 */
export function MemoMarkdown({ content }: MemoMarkdownProps) {
  return (
    <div className="markdown-body text-sm leading-relaxed text-slate-800 break-words">
      <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
