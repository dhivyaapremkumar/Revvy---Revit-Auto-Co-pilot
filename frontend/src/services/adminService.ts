// Admin Panel API calls (Module 5 in PRPs/revvy-prp.md).
import api from './api';
import type { AdminStats, AdminUserUpdatePayload, CodeDocument, User } from '../types';

export const adminService = {
  async listUsers(): Promise<User[]> {
    const { data } = await api.get<User[]>('/admin/users');
    return data;
  },

  async updateUser(userId: number, payload: AdminUserUpdatePayload): Promise<User> {
    const { data } = await api.put<User>(`/admin/users/${userId}`, payload);
    return data;
  },

  async getStats(): Promise<AdminStats> {
    const { data } = await api.get<AdminStats>('/admin/stats');
    return data;
  },

  async listCodeDocuments(): Promise<CodeDocument[]> {
    const { data } = await api.get<CodeDocument[]>('/admin/code-documents');
    return data;
  },
};
