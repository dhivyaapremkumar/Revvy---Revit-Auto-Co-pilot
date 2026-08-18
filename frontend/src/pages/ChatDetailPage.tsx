import { useParams } from 'react-router-dom';
import { Grid, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { SessionList } from '../components/chat/SessionList';
import { ChatWindow } from '../components/chat/ChatWindow';

/** /chat/:sessionId -- session list + the active conversation. */
export function ChatDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const parsedId = sessionId ? Number(sessionId) : NaN;

  return (
    <PageWrapper>
      <NavBar />
      <Grid templateColumns={{ base: '1fr', md: '320px 1fr' }} gap={6} px={6} py={8} maxW="6xl" mx="auto" h="calc(100vh - 140px)">
        <GlassCard overflowY="auto">
          <SessionList activeSessionId={Number.isNaN(parsedId) ? undefined : parsedId} />
        </GlassCard>
        <GlassCard display="flex" flexDirection="column" minH={0}>
          {Number.isNaN(parsedId) ? (
            <Text color="red.500">Invalid chat session.</Text>
          ) : (
            <ChatWindow sessionId={parsedId} />
          )}
        </GlassCard>
      </Grid>
    </PageWrapper>
  );
}
