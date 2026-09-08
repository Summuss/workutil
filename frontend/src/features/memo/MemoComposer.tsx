import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import type { ImageUpload } from "../../shared/images";
import { useImageAttachments } from "../../shared/useImageAttachments";

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
      setError(messageOf(cause, t("memo.save_failed")));
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
    <div className="card flex flex-col p-4">
      <textarea
        ref={textarea}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        rows={3}
        spellCheck={false}
        placeholder={t("memo.composer_placeholder")}
        className="w-full resize-y border-none bg-transparent leading-relaxed outline-none"
        style={{ fontFamily: "var(--mono)", fontSize: "13.5px", color: "var(--text)" }}
      />
      <div className="mt-2 flex items-center justify-end gap-2.5">
        {error !== null && (
          <span className="mr-auto text-xs" style={{ color: "var(--danger)" }}>
            {error}
          </span>
        )}
        <span className="text-[11.5px]" style={{ fontFamily: "var(--mono)", color: "var(--text-faint)" }}>
          {saving ? t("common.saving") : t("memo.ctrl_enter_save")}
        </span>
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving || body.trim() === ""}
          className="btn-primary"
        >
          {t("common.save")}
        </button>
      </div>
    </div>
  );
}
