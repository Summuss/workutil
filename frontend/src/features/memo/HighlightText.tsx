interface HighlightTextProps {
  text: string;
  query: string;
}

/**
 * Safely renders text with occurrences of query highlighted using <mark>.
 * Zero raw HTML or dangerouslySetInnerHTML to preserve XSS safety (design.md §2).
 */
export function HighlightText({ text, query }: HighlightTextProps) {
  const q = query.trim();
  if (!q) {
    return <>{text}</>;
  }

  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "i");
  const parts = text.split(regex);

  return (
    <span>
      {parts.map((part, index) =>
        part.toLowerCase() === q.toLowerCase() ? (
          <mark
            key={index}
            className="rounded-xs bg-amber-200 px-0.5 font-medium text-slate-900"
          >
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </span>
  );
}
