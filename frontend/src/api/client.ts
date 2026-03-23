const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
export const DEFAULT_API_TIMEOUT_MS = 10000

export type ApiRequestOptions = RequestInit & {
  timeoutMs?: number
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function buildUrl(path: string) {
  return `${API_BASE_URL}${path}`
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_API_TIMEOUT_MS
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(buildUrl(path), {
      ...options,
      timeoutMs,
      signal: options.signal ?? controller.signal,
    } as ApiRequestOptions)

    if (!response.ok) {
      const detail = await readErrorMessage(response)
      throw new ApiError(detail, response.status)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('Request timed out. Please try again.', 408)
    }
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

async function readErrorMessage(response: Response) {
  try {
    const payload = await response.json() as { detail?: string }
    return payload.detail ?? `Request failed with status ${response.status}`
  } catch {
    return `Request failed with status ${response.status}`
  }
}
