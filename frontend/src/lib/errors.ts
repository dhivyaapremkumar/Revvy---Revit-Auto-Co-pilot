// Shared helper for turning an unknown caught error (typically an Axios
// error wrapping an ApiErrorResponse) into a single displayable string.
// Used by every form (login, register, chat, code search, ...) so error
// rendering is consistent across modules.
import { isAxiosError } from 'axios';
import type { ApiErrorResponse } from '../types';

export function getErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((item) => item.msg).join(', ');
    }
    if (error.message) {
      return error.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
