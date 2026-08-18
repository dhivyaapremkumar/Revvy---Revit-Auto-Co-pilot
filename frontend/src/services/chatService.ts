// Chat Copilot API calls (Module 2 in PRPs/revvy-prp.md).
import api from './api';
import type {
  ChatMessage,
  ChatSession,
  ChatSessionWithMessages,
  CreateChatSessionPayload,
  SendChatMessagePayload,
} from '../types';

export const chatService = {
  async listSessions(): Promise<ChatSession[]> {
    const { data } = await api.get<ChatSession[]>('/chat/sessions');
    return data;
  },

  async createSession(payload: CreateChatSessionPayload = {}): Promise<ChatSession> {
    const { data } = await api.post<ChatSession>('/chat/sessions', payload);
    return data;
  },

  async getSession(sessionId: number): Promise<ChatSessionWithMessages> {
    const { data } = await api.get<ChatSessionWithMessages>(`/chat/sessions/${sessionId}`);
    return data;
  },

  async deleteSession(sessionId: number): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  async sendMessage(sessionId: number, payload: SendChatMessagePayload): Promise<ChatMessage> {
    const { data } = await api.post<ChatMessage>(`/chat/sessions/${sessionId}/messages`, payload);
    return data;
  },
};
