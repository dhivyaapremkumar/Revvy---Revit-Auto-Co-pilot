// React Query hooks wrapping chatService, used by ChatListPage/ChatDetailPage
// and components/chat/*.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatService } from '../services/chatService';
import type { CreateChatSessionPayload, SendChatMessagePayload } from '../types';

const SESSIONS_KEY = ['chat', 'sessions'] as const;
const sessionKey = (sessionId: number) => ['chat', 'sessions', sessionId] as const;

export function useChatSessions() {
  return useQuery({ queryKey: SESSIONS_KEY, queryFn: chatService.listSessions });
}

export function useChatSession(sessionId: number | undefined) {
  return useQuery({
    queryKey: sessionKey(sessionId ?? -1),
    queryFn: () => chatService.getSession(sessionId as number),
    enabled: sessionId !== undefined,
  });
}

export function useCreateChatSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload?: CreateChatSessionPayload) => chatService.createSession(payload ?? {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}

export function useDeleteChatSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: number) => chatService.deleteSession(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}

export function useSendChatMessage(sessionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SendChatMessagePayload) => chatService.sendMessage(sessionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}

/** Creates a session and sends `content` as its first message in one step, for the dashboard "ask bar". */
export function useAskRevvy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (content: string) => {
      const session = await chatService.createSession({ title: content.slice(0, 60) });
      await chatService.sendMessage(session.id, { content });
      return session;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}
