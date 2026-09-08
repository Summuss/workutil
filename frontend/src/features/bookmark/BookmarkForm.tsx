import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import { extractNameFromPath } from "./pathUtil";
import type { BookmarkCreatePayload, BookmarkGroup } from "./types";

interface BookmarkFormProps {
  groups: BookmarkGroup[];
  onRegister: (payload: BookmarkCreatePayload) => Promise<void>;
  onCancel: () => void;
}

export function BookmarkForm({ groups, onRegister, onCancel }: BookmarkFormProps) {
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [groupId, setGroupId] = useState<number | null>(null);
  const [userEditedName, setUserEditedName] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handlePathChange(rawPath: string) {
    setPath(rawPath);
    setError(null);
    if (!userEditedName || name.trim() === "") {
      const extracted = extractNameFromPath(rawPath);
      setName(extracted);
    }
  }

  function handleNameChange(newName: string) {
    setName(newName);
    setUserEditedName(true);
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const cleanPath = path.trim().replace(/^["']|["']$/g, "");
    const cleanName = name.trim();

    if (!cleanPath || !cleanName || submitting) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onRegister({
        path: cleanPath,
        name: cleanName,
        group_id: groupId ?? undefined,
      });
      setPath("");
      setName("");
      setUserEditedName(false);
    } catch (cause) {
      setError(messageOf(cause, t("bookmark.create_failed")));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="card flex flex-col gap-2.5 p-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="bookmark-path" className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          {t("bookmark.path_label")}
        </label>
        <input
          id="bookmark-path"
          type="text"
          value={path}
          onChange={(e) => handlePathChange(e.target.value)}
          placeholder={t("bookmark.path_placeholder")}
          className="field-input"
          autoFocus
        />
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label htmlFor="bookmark-name" className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {t("bookmark.name_label")}
          </label>
          <input
            id="bookmark-name"
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder={t("bookmark.name_placeholder")}
            className="field-input"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="bookmark-group" className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {t("bookmark.group_label")}
          </label>
          <select
            id="bookmark-group"
            value={groupId ?? ""}
            onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
            className="field-input"
          >
            <option value="">{t("bookmark.no_group_option")}</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error !== null && (
        <p className="text-[11.5px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
          style={{ fontSize: "12px", padding: "6px 13px", borderRadius: "6px" }}
        >
          {t("common.cancel")}
        </button>
        <button
          type="submit"
          disabled={submitting || path.trim() === "" || name.trim() === ""}
          className="btn-primary"
          style={{ fontSize: "12px", padding: "6px 13px", borderRadius: "6px" }}
        >
          {submitting ? t("bookmark.submitting") : t("bookmark.submit_button")}
        </button>
      </div>
    </form>
  );
}
