// Split from AuthContext.tsx so that file only exports the AuthProvider
// component (keeps react-refresh/only-export-components happy).
import { createContext } from 'react';
import type { LoginPayload, RegisterPayload, UpdateProfilePayload, User } from '../types';

export interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
