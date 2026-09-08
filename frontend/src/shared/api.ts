import { t } from "./i18n";

/** Talking to the workutil backend, which is always same-origin. */

const API_ROOT = "/api";

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Why the server said no, localized by error code when possible.
 *
 * Evidence rejects a case name at the moment it is typed rather than cleaning
 * it up at export, and that only helps if the reason reaches the field the
 * author is looking at. Structured codes allow front-end localization.
 */
export async function refusalFrom(response: Response): Promise<string> {
  if (response.status >= 500) {
    return t("error.unknown");
  }

  const generic = t("api.request_failed", { status: response.status });
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null) {
      const b = body as Record<string, unknown>;
      let code: string | null = null;
      if (typeof b.code === "string" && b.code.trim() !== "") {
        code = b.code.trim();
      } else if (typeof b.detail === "object" && b.detail !== null) {
        const d = b.detail as Record<string, unknown>;
        if (typeof d.code === "string" && d.code.trim() !== "") {
          code = d.code.trim();
        }
      }

      if (code) {
        const errorKey = `error.${code}`;
        const translated = t(errorKey);
        if (translated !== `[${errorKey}]`) {
          return translated;
        }
      }

      if (typeof b.detail === "string" && b.detail.trim() !== "") {
        return b.detail;
      }
      if (typeof b.detail === "object" && b.detail !== null) {
        const d = b.detail as Record<string, unknown>;
        if (typeof d.message === "string" && d.message.trim() !== "") {
          return d.message;
        }
      }
    }
    return generic;
  } catch {
    return generic;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, init);
  } catch {
    throw new ApiError(0, t("api.network_error"));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await refusalFrom(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

/** What to show the user when a request threw. */
export function messageOf(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

/** `payload` is optional: a POST can be a verb whose object the server already
    has, and then there is nothing to send. */
export function post<T>(path: string, payload?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function patch<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function put<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Deleting usually answers with nothing, but not always — so what comes back
    is left to the caller to name. */
export function del<T = void>(path: string): Promise<T> {
  return request<T>(path, {
    method: "DELETE",
  });
}

