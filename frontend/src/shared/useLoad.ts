import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { messageOf } from "./api";
import { t } from "./i18n";

export interface Loaded<T> {
  value: T | null;
  setValue: Dispatch<SetStateAction<T | null>>;
  loading: boolean;
  error: string | null;
  setError: Dispatch<SetStateAction<string | null>>;
}

/**
 * Fetch one thing when a page opens, and hand back what to draw meanwhile.
 *
 * `setValue` is exposed because every page here edits what it loaded and shows
 * the result immediately, rather than refetching the list after each change.
 *
 * `load` is intentionally not a dependency: pages pass an inline closure, which
 * is a new function on every render and would refetch forever. `deps` says what
 * the fetch actually varies with — an id from the URL, usually.
 */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[] = []): Loaded<T> {
  const [value, setValue] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let abandoned = false;
    setLoading(true);

    load()
      .then((loaded) => {
        if (!abandoned) {
          setValue(loaded);
          setError(null);
        }
      })
      .catch((cause: unknown) => {
        if (!abandoned) {
          setError(messageOf(cause, t("common.load_failed")));
        }
      })
      .finally(() => {
        if (!abandoned) {
          setLoading(false);
        }
      });

    // A page left mid-flight must not write into state that is gone.
    return () => {
      abandoned = true;
    };
  }, deps);

  return { value, setValue, loading, error, setError };
}
