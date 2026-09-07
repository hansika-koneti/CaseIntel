/**
 * CaseIntel — Base API client
 *
 * Thin wrapper around fetch() that:
 *  - Reads the backend URL from VITE_API_URL env var
 *  - Sets JSON headers on mutating requests
 *  - Throws a typed ApiError on non-2xx responses
 *  - Recursively normalises snake_case keys → camelCase so all
 *    callers work with the frontend's TypeScript types directly
 */

// ── Configuration ─────────────────────────────────────────────────────────
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8000';

// ── Typed error ───────────────────────────────────────────────────────────
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

// ── snake_case → camelCase normaliser ────────────────────────────────────
/** Convert "some_key" → "someKey" */
function toCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

/** Recursively walk a JSON value and convert all object keys to camelCase. */
export function normaliseToCamel<T = unknown>(value: unknown): T {
  if (Array.isArray(value)) {
    return value.map(normaliseToCamel) as T;
  }
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        toCamel(k),
        normaliseToCamel(v),
      ]),
    ) as T;
  }
  return value as T;
}

/** Recursively convert camelCase keys → snake_case for request bodies. */
function toSnake(s: string): string {
  return s.replace(/([A-Z])/g, (c) => `_${c.toLowerCase()}`);
}

export function normaliseToSnake<T = unknown>(value: unknown): T {
  if (Array.isArray(value)) {
    return value.map(normaliseToSnake) as T;
  }
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        toSnake(k),
        normaliseToSnake(v),
      ]),
    ) as T;
  }
  return value as T;
}

// ── Core fetch wrapper ────────────────────────────────────────────────────
interface FetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * Make an authenticated API request.
 * Response JSON is automatically normalised to camelCase.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { method = 'GET', body, signal } = options;

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    // Serialise body with snake_case keys to match the FastAPI Pydantic models
    body: body !== undefined ? JSON.stringify(normaliseToSnake(body)) : undefined,
    signal,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errJson = (await response.json()) as { detail?: string };
      detail = errJson.detail ?? detail;
    } catch {
      // ignore parse errors; use statusText
    }
    throw new ApiError(response.status, detail);
  }

  const json: unknown = await response.json();
  return normaliseToCamel<T>(json);
}
