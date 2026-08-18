import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Spinner, Text, VStack } from '@chakra-ui/react';
import { MessageBubble } from './MessageBubble';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { InlineBanner } from '../ui/InlineBanner';
import { FormStack } from '../ui/FormStack';
import { useChatSession, useSendChatMessage } from '../../hooks/useChat';
import { getErrorMessage } from '../../lib/errors';

export interface ChatWindowProps {
  sessionId: number;
}

/** Message history + composer for one chat session. */
export function ChatWindow({ sessionId }: ChatWindowProps) {
  const { data: session, isLoading } = useChatSession(sessionId);
  const sendMessage = useSendChatMessage(sessionId);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content) {
      return;
    }
    setError(null);
    sendMessage.mutate(
      { content },
      {
        onSuccess: () => setDraft(''),
        onError: (err) => setError(getErrorMessage(err, 'Could not send your message.')),
      },
    );
  };

  if (isLoading) {
    return <Spinner alignSelf="center" color="brand.500" mx="auto" mt={10} />;
  }

  return (
    <VStack align="stretch" h="full" gap={4}>
      <VStack align="stretch" flex={1} overflowY="auto" gap={3} py={2}>
        {session?.messages.length ? (
          session.messages.map((message) => <MessageBubble key={message.id} message={message} />)
        ) : (
          <Text color="gray.500" _dark={{ color: 'gray.400' }} textAlign="center" mt={10}>
            Ask REVVY anything about your Revit workflow.
          </Text>
        )}
      </VStack>

      {error && <InlineBanner status="error">{error}</InlineBanner>}

      <FormStack onSubmit={handleSubmit} gap={2} alignItems="stretch">
        <AnimatedInput
          placeholder="Type a message..."
          value={draft}
          onChange={(event: ChangeEvent<HTMLInputElement>) => setDraft(event.target.value)}
        />
        <GradientButton type="submit" isLoading={sendMessage.isPending} alignSelf="flex-end">
          Send
        </GradientButton>
      </FormStack>
    </VStack>
  );
}
