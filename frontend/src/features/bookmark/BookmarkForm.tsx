import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { extractNameFromPath } from "./pathUtil";
import type { BookmarkCreatePayload } from "./types";

interface BookmarkFormProps {
  onRegister: (payload: BookmarkCreatePayload) => Promise<void>;
}

export function BookmarkForm({ onRegister }: BookmarkFormProps) {
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
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
      await onRegister({ path: cleanPath, name: cleanName });
      setPath("");
      setName("");
      setUserEditedName(false);
    } catch (cause) {
      setError(messageOf(cause, "登记失败"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-1">
        <label htmlFor="bookmark-path" className="text-xs font-medium text-slate-700">
          路径
        </label>
        <input
          id="bookmark-path"
          type="text"
          value={path}
          onChange={(e) => handlePathChange(e.target.value)}
          placeholder="粘贴文件或文件夹路径 (如 Windows 复制路径、macOS 绝对路径)"
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
          autoFocus
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="bookmark-name" className="text-xs font-medium text-slate-700">
          名称
        </label>
        <input
          id="bookmark-name"
          type="text"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder="书签显示名称 (粘贴路径后自动预填文件名,可修改)"
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
        />
      </div>

      {error !== null && <p className="text-xs text-red-600">{error}</p>}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitting || path.trim() === "" || name.trim() === ""}
          className="cursor-pointer rounded-md bg-slate-800 px-4 py-2 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {submitting ? "登记中…" : "登记书签"}
        </button>
      </div>
    </form>
  );
}
