import type {
  CurrentUserResponse,
  CSRFResponse,
  LoginResponse,
} from '../types/auth';

export class ApiError extends Error {
  status: number;
  detail: string;
  isNetworkError: boolean;

  constructor(status: number, message: string, detail?: string, isNetworkError = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail || message;
    this.isNetworkError = isNetworkError;
  }
}

// In-memory CSRF token store (never persisted to localStorage/sessionStorage)
let inMemoryCsrfToken: string | null = null;

export function getCachedCsrfToken(): string | null {
  return inMemoryCsrfToken;
}

export function clearCachedCsrfToken(): void {
  inMemoryCsrfToken = null;
}

const API_BASE =
  (typeof import.meta !== 'undefined' &&
    (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL) ||
  '';

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  requiresCsrf = false
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  headers.set('Accept', 'application/json');

  const method = (options.method || 'GET').toUpperCase();
  const isStateModifying = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

  if (isStateModifying || requiresCsrf) {
    if (!inMemoryCsrfToken) {
      await fetchCsrfToken();
    }
    if (inMemoryCsrfToken) {
      headers.set('X-CSRF-Token', inMemoryCsrfToken);
    }
  }

  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Mandatory: conveys HttpOnly JWT cookie and CSRF cookie
    });
  } catch (error) {
    throw new ApiError(
      0,
      'Network connection failure. The verification server may be offline.',
      error instanceof Error ? error.message : 'Unknown network failure',
      true
    );
  }

  // Handle successful response
  if (response.ok) {
    if (response.status === 204) {
      return {} as T;
    }
    return (await response.json()) as T;
  }

  // Parse error payload from backend (FastAPI formats errors as { "detail": ... })
  let detail = 'An unexpected error occurred.';
  try {
    const errorJson = await response.json();
    if (typeof errorJson.detail === 'string') {
      detail = errorJson.detail;
    } else if (Array.isArray(errorJson.detail)) {
      // Pydantic validation error array
      detail = errorJson.detail.map((d: { msg?: string }) => d.msg || '').join(', ');
    } else if (typeof errorJson.message === 'string') {
      detail = errorJson.message;
    }
  } catch {
    detail = response.statusText || `Request failed with status ${response.status}`;
  }

  // If a state-modifying request failed with 403 CSRF error, clear in-memory CSRF token
  if (response.status === 403 && detail.toLowerCase().includes('csrf')) {
    inMemoryCsrfToken = null;
  }

  throw new ApiError(response.status, detail, detail, false);
}

export async function fetchCsrfToken(): Promise<string> {
  const data = await request<CSRFResponse>('/api/v1/auth/csrf', { method: 'GET' });
  inMemoryCsrfToken = data.csrf_token;
  return data.csrf_token;
}

export const api = {
  auth: {
    csrf: fetchCsrfToken,

    async login(email: string, password: string): Promise<LoginResponse> {
      // Ensure we have a fresh CSRF token prior to login attempt
      await fetchCsrfToken();
      return request<LoginResponse>(
        '/api/v1/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        },
        true
      );
    },

    async me(): Promise<CurrentUserResponse> {
      return request<CurrentUserResponse>('/api/v1/auth/me', {
        method: 'GET',
      });
    },

    async logout(): Promise<void> {
      try {
        await request<{ message: string }>(
          '/api/v1/auth/logout',
          {
            method: 'POST',
          },
          true
        );
      } finally {
        clearCachedCsrfToken();
      }
    },
  },
};
