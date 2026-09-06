import { ApiError } from './types'

export const API_BASE_URL_STORAGE_KEY = 'mlsecops:apiBaseUrl'

/** The API base URL every page reads from, writable via Settings  */
export function getApiBaseUrl(): string {
  const stored = localStorage.getItem(API_BASE_URL_STORAGE_KEY)
  if (stored && stored.trim().length > 0) return stored
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
}

export function setApiBaseUrl(url: string): void {
  localStorage.setItem(API_BASE_URL_STORAGE_KEY, url)
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  signal?: AbortSignal
}

/**
 * Thin fetch wrapper. Throws ApiError with the parsed response body on any
 * non-2xx status, so callers can branch on .status (422 / 503 / 500).
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const base = getApiBaseUrl()
  const url = `${base.replace(/\/$/, '')}${path}`

  let response: Response
  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (err) {
    // Let an intentional cancellation propagate as-is so callers can tell
    // "user cancelled" apart from "the request actually failed" — wrapping
    // it in ApiError would make both look identical downstream.
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(err instanceof Error ? err.message : 'Network request failed', 0, null)
  }

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const payload = isJson ? await response.json().catch(() => null) : await response.text()

  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with ${response.status}`, response.status, payload)
  }

  return payload as T
}
