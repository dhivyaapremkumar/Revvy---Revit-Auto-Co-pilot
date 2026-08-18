import { Grid, Text, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { SessionList } from '../components/chat/SessionList';

/** /chat -- session list with no conversation selected yet. */
export function ChatListPage() {
  return (
    <PageWrapper>
      <NavBar />
      <Grid templateColumns={{ base: '1fr', md: '320px 1fr' }} gap={6} px={6} py={8} maxW="6xl" mx="auto">
        <GlassCard>
          <SessionList />
        </GlassCard>
        <GlassCard display={{ base: 'none', md: 'flex' }} alignItems="center" justifyContent="center">
          <VStack>
            <Text fontSize="lg" fontWeight="medium">
              Select a conversation
            </Text>
            <Text color="gray.500" _dark={{ color: 'gray.400' }} fontSize="sm">
              Or start a new chat from the sidebar.
            </Text>
          </VStack>
        </GlassCard>
      </Grid>
    </PageWrapper>
  );
}
