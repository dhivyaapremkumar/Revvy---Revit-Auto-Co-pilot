import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../services/adminService';
import type { AdminUserUpdatePayload } from '../types';

const USERS_KEY = ['admin', 'users'] as const;
const STATS_KEY = ['admin', 'stats'] as const;
const CODE_DOCUMENTS_KEY = ['admin', 'code-documents'] as const;

export function useAdminUsers() {
  return useQuery({ queryKey: USERS_KEY, queryFn: adminService.listUsers });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: number; payload: AdminUserUpdatePayload }) =>
      adminService.updateUser(userId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useAdminStats() {
  return useQuery({ queryKey: STATS_KEY, queryFn: adminService.getStats });
}

export function useAdminCodeDocuments() {
  return useQuery({ queryKey: CODE_DOCUMENTS_KEY, queryFn: adminService.listCodeDocuments });
}
