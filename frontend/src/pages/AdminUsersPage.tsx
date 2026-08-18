import { Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { UserTable } from '../components/admin/UserTable';

/** /admin/users -- manage user active/admin status. */
export function AdminUsersPage() {
  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="6xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Users</Heading>
        <GlassCard>
          <UserTable />
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
