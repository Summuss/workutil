import { useState, type Dispatch, type SetStateAction } from "react";

import { messageOf } from "./api";

export interface EditRunner {
  busy: boolean;
  error: string | null;
  setError: Dispatch<SetStateAction<string | null>>;
  run: (change: () => Promise<void>) => Promise<boolean>;
}

/**
 * Run one edit at a time, keeping the server's own reason when it refuses.
 *
 * `run` answers whether the change was accepted rather than throwing, so a
 * refused value can stay on screen in the field it was typed in with the
 * reason under it — which is the whole point of catching an illegal sheet name
 * as it is typed instead of at export (design.md §6 F5).
 *
 * `fallback` is what to say when the failure carries no message of its own.
 */
export function useEditRunner(fallback: string): EditRunner {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(change: () => Promise<void>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      await change();
      return true;
    } catch (cause) {
      setError(messageOf(cause, fallback));
      return false;
    } finally {
      setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
