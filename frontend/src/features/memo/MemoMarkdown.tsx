import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";

import { Lightbox } from "../../shared/Lightbox";

interface MemoMarkdownProps {
  content: string;
}

/**
 * Renders memo markdown safely:
 * - Code blocks display in monospace font with syntax highlighting.
 * - Raw HTML tags and scripts are escaped to plain text, never executed by the browser.
 * - Clicking thumbnail images opens the Lightbox.
 */
export function MemoMarkdown({ content }: MemoMarkdownProps) {
  const [activeImage, setActiveImage] = useState<string | null>(null);

  return (
    <>
      <div className="markdown-body break-words text-[13.5px] leading-relaxed" style={{ color: "var(--text)" }}>
        <ReactMarkdown
          rehypePlugins={[rehypeHighlight]}
          components={{
            img: ({ src, alt }) => {
              if (!src) return null;
              return (
                <img
                  src={src}
                  alt={alt ?? ""}
                  onClick={() => setActiveImage(src)}
                />
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {activeImage && (
        <Lightbox
          src={activeImage}
          onClose={() => setActiveImage(null)}
        />
      )}
    </>
  );
}
