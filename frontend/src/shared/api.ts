/** Talking to the workutil backend, which is always same-origin. */

const API_ROOT = "/api";

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Why the server said no, in its own words.
 *
 * Evidence rejects a case name at the moment it is typed rather than cleaning
 * it up at export, and that only helps if the reason reaches the field the
 * author is looking at. FastAPI's own validation errors put a list of objects
 * in `detail`; those have nothing to say to a person, so they fall back.
 */
async function refusalFrom(response: Response): Promise<string> {
  const generic = `请求失败(${response.status})`;
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    return typeof detail === "string" && detail.trim() !== "" ? detail : generic;
  } catch {
    return generic;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, init);
  } catch {
    throw new ApiError(0, "连接不上 workutil 服务");
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

export function post<T>(path: string, payload: unknown): Promise<T> {
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

export function del(path: string): Promise<void> {
  return request<void>(path, {
    method: "DELETE",
  });
}

