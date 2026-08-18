import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, HStack, Spinner, Text, VStack } from '@chakra-ui/react';
import { AnimatedList } from '../ui/AnimatedList';
import { GradientButton } from '../ui/GradientButton';
import { MotionButton } from '../../lib/motion';
import type { ChatSession } from '../../types';
import { useChatSessions, useCreateChatSession, useDeleteChatSession } from '../../hooks/useChat';

export interface SessionListProps {
  activeSessionId?: number;
}

/** Sidebar list of chat sessions, shared by ChatListPage and ChatDetailPage. */
export function SessionList({ activeSessionId }: SessionListProps) {
  const { data: sessions, isLoading } = useChatSessions();
  const createSession = useCreateChatSession();
  const deleteSession = useDeleteChatSession();
  const navigate = useNavigate();

  const handleNewSession = () => {
    createSession.mutate(undefined, {
      onSuccess: (session) => navigate(`/chat/${session.id}`),
    });
  };

  return (
    <VStack align="stretch" gap={4} w="full">
      <GradientButton onClick={handleNewSession} isLoading={createSession.isPending} w="full">
        New chat
      </GradientButton>

      {isLoading ? (
        <Spinner alignSelf="center" color="brand.500" />
      ) : (
        <AnimatedList<ChatSession>
          items={sessions ?? []}
          getKey={(session) => session.id}
          emptyState={
            <Text fontSize="sm" color="gray.500" _dark={{ color: 'gray.400' }}>
              No conversations yet. Start one above.
            </Text>
          }
          renderItem={(session) => (
            <HStack
              justify="space-between"
              px={3}
              py={2}
              borderRadius="lg"
              bg={session.id === activeSessionId ? 'brand.50' : 'transparent'}
              _dark={{ bg: session.id === activeSessionId ? 'blackAlpha.400' : 'transparent' }}
              _hover={{ bg: 'brand.50' }}
            >
              <Box asChild flex={1} minW={0}>
                <RouterLink to={`/chat/${session.id}`}>
                  <Text fontSize="sm" fontWeight="medium" truncate>
                    {session.title ?? `Session #${session.id}`}
                  </Text>
                </RouterLink>
              </Box>
              <MotionButton
                type="button"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                fontSize="xs"
                color="red.500"
                bg="transparent"
                onClick={() => deleteSession.mutate(session.id)}
              >
                Delete
              </MotionButton>
            </HStack>
          )}
        />
      )}
    </VStack>
  );
}
