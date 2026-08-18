import { Heading, Spinner, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { InlineBanner } from '../components/ui/InlineBanner';
import { StatsSummary } from '../components/admin/StatsSummary';
import { useAdminStats } from '../hooks/useAdmin';
import { getErrorMessage } from '../lib/errors';

/** /admin -- platform stats overview. */
export function AdminDashboardPage() {
  const { data: stats, isLoading, isError, error } = useAdminStats();

  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="6xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Admin Dashboard</Heading>

        {isLoading && <Spinner color="brand.500" />}
        {isError && (
          <InlineBanner status="error">{getErrorMessage(error, 'Could not load platform stats.')}</InlineBanner>
        )}
        {stats && (
          <GlassCard>
            <StatsSummary stats={stats} />
          </GlassCard>
        )}
      </VStack>
    </PageWrapper>
  );
}
