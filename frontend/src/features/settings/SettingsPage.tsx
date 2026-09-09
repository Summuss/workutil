import { useRef, useState, type ChangeEvent } from "react";

import { refusalFrom } from "../../shared/api";
import { useI18n } from "../../shared/i18n";
import { PageLayout } from "../../shared/PageLayout";

export function SettingsPage() {
  const { t } = useI18n();

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Import state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<{
    backupFile: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleExport() {
    if (exporting) return;
    setExporting(true);
    setExportError(null);

    try {
      const res = await fetch("/api/transfer/export");
      if (!res.ok) {
        const msg = await refusalFrom(res);
        setExportError(msg);
        return;
      }

      // Extract filename from header or fallback
      const disposition = res.headers.get("content-disposition");
      let filename = "workutil-data.zip";
      if (disposition) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match?.[1]) {
          filename = match[1];
        }
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setExportError(t("settings.export_failed"));
    } finally {
      setExporting(false);
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setImportError(null);
    setImportSuccess(null);
  }

  async function handleConfirmImport() {
    if (!selectedFile || importing) return;

    setImporting(true);
    setImportError(null);
    setImportSuccess(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("/api/transfer/import", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const msg = await refusalFrom(res);
        setImportError(msg);
        setShowConfirm(false);
        return;
      }

      const data = (await res.json()) as {
        restart_required: boolean;
        backup_file: string;
      };
      setImportSuccess({ backupFile: data.backup_file });
      setShowConfirm(false);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      setImportError(t("error.unknown"));
      setShowConfirm(false);
    } finally {
      setImporting(false);
    }
  }

  return (
    <PageLayout>
      <div className="flex flex-col gap-6 py-2">
        {/* Page title and description */}
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight">
            {t("settings.title")}
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {t("settings.desc")}
          </p>
        </div>

        {/* Success restart banner */}
        {importSuccess && (
          <div
            className="flex flex-col gap-2.5 rounded-lg p-5"
            style={{
              background: "var(--success-tint)",
              border: "1.5px solid var(--success)",
              color: "var(--text)",
            }}
          >
            <div className="flex items-center gap-2">
              <span className="text-base font-bold" style={{ color: "var(--success)" }}>
                ✓
              </span>
              <h2 className="text-base font-bold tracking-tight">
                {t("settings.import_success_title")}
              </h2>
            </div>
            <p className="text-sm leading-relaxed">
              {t("settings.import_success_desc", { backup: importSuccess.backupFile })}
            </p>
            <div
              className="mt-1 rounded px-3 py-2 text-xs font-semibold"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                color: "var(--accent-strong)",
              }}
            >
              ⚠ {t("settings.restart_instruction")}
            </div>
          </div>
        )}

        {/* Section 1: Export */}
        <section
          className="flex flex-col gap-3.5 rounded-lg p-5"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
          }}
        >
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">
              {t("settings.export_title")}
            </h2>
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {t("settings.export_desc")}
            </p>
          </div>

          <div>
            <button
              type="button"
              onClick={handleExport}
              disabled={exporting}
              className="btn-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
            >
              {exporting ? t("settings.exporting") : t("settings.export_button")}
            </button>
          </div>

          {exportError && (
            <div
              className="rounded-md px-3 py-2 text-xs"
              style={{
                background: "var(--danger-tint)",
                color: "var(--danger)",
                border: "1px solid var(--danger)",
              }}
            >
              {exportError}
            </div>
          )}
        </section>

        {/* Section 2: Import */}
        <section
          className="flex flex-col gap-3.5 rounded-lg p-5"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
          }}
        >
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold">
              {t("settings.import_title")}
            </h2>
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {t("settings.import_desc")}
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip,application/zip"
                onChange={handleFileChange}
                className="hidden"
                id="import-zip-input"
              />
              <label
                htmlFor="import-zip-input"
                className="cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
                style={{
                  background: "var(--hover-wash)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                }}
              >
                {t("settings.import_choose_file")}
              </label>
              <span
                className="text-xs truncate max-w-xs"
                style={{ color: selectedFile ? "var(--text)" : "var(--text-faint)" }}
              >
                {selectedFile ? selectedFile.name : t("settings.import_no_file")}
              </span>
            </div>

            <div>
              <button
                type="button"
                onClick={() => setShowConfirm(true)}
                disabled={!selectedFile || importing}
                className="btn-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
              >
                {importing ? t("settings.importing") : t("settings.import_button")}
              </button>
            </div>
          </div>

          {importError && (
            <div
              className="rounded-md px-3 py-2 text-xs"
              style={{
                background: "var(--danger-tint)",
                color: "var(--danger)",
                border: "1px solid var(--danger)",
              }}
            >
              {importError}
            </div>
          )}
        </section>

        {/* Confirmation Modal */}
        {showConfirm && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "var(--scrim)" }}
          >
            <div
              className="flex w-full max-w-md flex-col gap-4 rounded-lg p-6 shadow-xl"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
              }}
            >
              <div className="flex flex-col gap-1.5">
                <h3 className="text-base font-semibold">
                  {t("settings.import_confirm_title")}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {t("settings.import_confirm_desc")}
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  disabled={importing}
                  className="cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium"
                  style={{
                    background: "var(--hover-wash)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                  }}
                >
                  {t("settings.import_confirm_cancel")}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmImport}
                  disabled={importing}
                  className="btn-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {importing ? t("settings.importing") : t("settings.import_confirm_ok")}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
