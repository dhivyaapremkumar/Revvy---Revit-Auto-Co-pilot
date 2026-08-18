import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { useAuth } from '../../hooks/useAuth';

export interface ProtectedRouteProps {
  children: ReactNode;
  /** When true, also requires `user.is_admin` -- used by Admin Panel routes. */
  requireAdmin?: boolean;
}

/**
 * Gate for authenticated (and optionally admin-only) routes. Redirects
 * unauthenticated users to /login (preserving the intended destination),
 * and non-admin users hitting an admin route back to /chat.
 */
export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Center minH="100vh">
        <Spinner size="lg" color="brand.500" />
      </Center>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !user.is_admin) {
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
}
