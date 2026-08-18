// Shared Axios client for the REVVY backend (FastAPI, prefix /api/v1).
//
// Exports:
//   - `api` (default): configured Axios instance. Module agents should
//     import this and call `api.get/post/put/delete(...)` with relative
//     paths, e.g. `api.get('/chat/sessions')`.
//   - `tokenStorage`: read/write the JWT access + refresh tokens.
//
// On a 401 response, the client attempts one silent refresh via
// POST /auth/refresh, replays the original request, and otherwise clears
// tokens and redirects to /login. Concurrent 401s during an in-flight
// refresh are queued instead of triggering duplicate refresh calls.
import axios, { AxiosError } from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';
import type { AuthTokens } from '../types';

const API_BASE_URL = `${import.meta.env.VITE_API_URL}/api/v1`;

const ACCESS_TOKEN_KEY = 'revvy_access_token';
const REFRESH_TOKEN_KEY = 'revvy_refresh_token';

export const tokenStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens(tokens: Pick<AuthTokens, 'access_token' | 'refresh_token'>): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

function redirectToLogin(): void {
  if (typeof window !== 'undefined') {
    window.location.assign('/login');
  }
}

let isRefreshing = false;
let pendingResolvers: Array<() => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const status = error.response?.status;

    if (status !== 401 || !originalRequest || originalRequest._retry) {
      if (status === 401) {
        tokenStorage.clear();
        redirectToLogin();
      }
      return Promise.reject(error);
    }

    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) {
      tokenStorage.clear();
      redirectToLogin();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      await new Promise<void>((resolve) => pendingResolvers.push(resolve));
      return api(originalRequest);
    }

    isRefreshing = true;
    try {
      const { data } = await axios.post<AuthTokens>(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      tokenStorage.setTokens(data);
      pendingResolvers.forEach((resolve) => resolve());
      pendingResolvers = [];
      return api(originalRequest);
    } catch (refreshError) {
      tokenStorage.clear();
      pendingResolvers = [];
      redirectToLogin();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
