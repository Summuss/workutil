import {
  useCallback,
  useRef,
  useState,
  type ClipboardEvent,
  type DragEvent,
  type RefObject,
} from "react";

import type { ImageUpload } from "../features/memo/types";

interface PendingImage {
  id: string;
  file: File;
  dataUrl: string;
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Handles pasting and dragging screenshots into a textarea.
 *
 * Images are kept as data URLs in client memory with unique temp tokens
 * (e.g. `![image](temp:img_...)`) inserted at the cursor position. When
 * saving, only images whose tokens remain in the text are submitted.
 */
export function useImageAttachments(
  textareaRef: RefObject<HTMLTextAreaElement | null>,
  onChangeText: (next: string) => void,
) {
  const [pendingImages, setPendingImages] = useState<PendingImage[]>([]);
  const pendingImagesRef = useRef<PendingImage[]>([]);
  pendingImagesRef.current = pendingImages;

  const insertImages = useCallback(
    async (files: File[]) => {
      if (files.length === 0) {
        return;
      }

      const element = textareaRef.current;
      const currentVal = element ? element.value : "";
      const start = element ? element.selectionStart : currentVal.length;
      const end = element ? element.selectionEnd : currentVal.length;

      const newPending: PendingImage[] = [];
      let insertMarkdown = "";

      for (const [i, file] of files.entries()) {
        const tempId = `temp:img_${Date.now()}_${i}_${Math.random().toString(36).slice(2, 7)}`;
        const dataUrl = await fileToDataUrl(file);
        newPending.push({ id: tempId, file, dataUrl });

        const prefix =
          start > 0 && !currentVal.slice(0, start).endsWith("\n") ? "\n" : "";
        insertMarkdown += `${prefix}![image](${tempId})\n`;
      }

      setPendingImages((prev) => [...prev, ...newPending]);

      const before = currentVal.slice(0, start);
      const after = currentVal.slice(end);
      const nextVal = before + insertMarkdown + after;
      onChangeText(nextVal);

      requestAnimationFrame(() => {
        if (element) {
          element.focus();
          const nextPos = start + insertMarkdown.length;
          element.setSelectionRange(nextPos, nextPos);
        }
      });
    },
    [textareaRef, onChangeText],
  );

  const handlePaste = useCallback(
    (event: ClipboardEvent<HTMLTextAreaElement>) => {
      const items = event.clipboardData?.items;
      if (!items) {
        return;
      }

      const files: File[] = [];
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            files.push(file);
          }
        }
      }


      if (files.length > 0) {
        event.preventDefault();
        void insertImages(files);
      }
    },
    [insertImages],
  );

  const handleDrop = useCallback(
    (event: DragEvent<HTMLTextAreaElement>) => {
      const files = Array.from(event.dataTransfer?.files || []).filter((f) =>
        f.type.startsWith("image/"),
      );
      if (files.length > 0) {
        event.preventDefault();
        void insertImages(files);
      }
    },
    [insertImages],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLTextAreaElement>) => {
    const hasImage = Array.from(event.dataTransfer?.items || []).some((item) =>
      item.type.startsWith("image/"),
    );
    if (hasImage) {
      event.preventDefault();
    }
  }, []);

  const getImagesForSave = useCallback((textToSave: string): ImageUpload[] => {
    return pendingImagesRef.current
      .filter((img) => textToSave.includes(img.id))
      .map((img) => ({
        id: img.id,
        data: img.dataUrl,
        filename: img.file.name || "screenshot.png",
      }));
  }, []);

  const clearPendingImages = useCallback(() => {
    setPendingImages([]);
    pendingImagesRef.current = [];
  }, []);

  return {
    handlePaste,
    handleDrop,
    handleDragOver,
    getImagesForSave,
    clearPendingImages,
  };
}
