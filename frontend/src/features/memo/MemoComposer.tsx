import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { useImageAttachments } from "../../shared/useImageAttachments";
import type { ImageUpload } from "./types";

interface MemoComposerProps {
  onSave: (body: string, images?: ImageUpload[]) => Promise<void>;
}

/**
 * The box the cursor is already sitting in when the page opens.
 *
 * Everything here serves one number: zero navigation clicks between opening
 * workutil and having written something down.
 */
export function MemoComposer({ onSave }: MemoComposerProps) {
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  const {
    handlePaste,
    handleDrop,
    handleDragOver,
    getImagesForSave,
    forgetSavedImages,
  } = useImageAttachments(textarea, setBody);

  useEffect(() => {
    textarea.current?.focus();
  }, []);

  async function save() {
    const pending = body;
    if (pending.trim() === "" || saving) {
      return;
    }

    const imagesToSave = getImagesForSave(pending);

    setSaving(true);
    setError(null);
    try {
      await onSave(pending, imagesToSave);
      // What was saved goes; anything typed while the save was in flight
      // stays, so those keystrokes are neither lost nor saved twice.
      setBody((current) =>
        current.startsWith(pending) ? current.slice(pending.length) : "",
      );
      forgetSavedImages(pending);
    } catch (cause) {
      setError(messageOf(cause, "保存失败"));
    } finally {
      setSaving(false);
      textarea.current?.focus();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // metaKey so the same muscle memory works on macOS.
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void save();
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea
        ref={textarea}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        rows={5}
        spellCheck={false}
        placeholder="随手记点什么… (可直接粘贴或拖拽截图)"
        className="w-full resize-y rounded-lg border border-slate-300 bg-white p-3 font-mono text-sm leading-relaxed text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
      />
      <div className="flex min-h-5 items-center justify-between text-xs">
        <span className="text-red-600">{error}</span>
        <span className="text-slate-400">
          {saving ? "保存中…" : "Ctrl+Enter 保存"}
        </span>
      </div>
    </div>
  );
}

