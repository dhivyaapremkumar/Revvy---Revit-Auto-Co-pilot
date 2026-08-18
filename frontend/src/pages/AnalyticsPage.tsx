import { Heading, Spinner, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { InlineBanner } from '../components/ui/InlineBanner';
import { StatsSummary } from '../components/admin/StatsSummary';
import { UsageCharts } from '../components/analytics/UsageCharts';
import { CitedSectionsList } from '../components/analytics/CitedSectionsList';
import { useAdminStats } from '../hooks/useAdmin';
import { getErrorMessage } from '../lib/errors';

/** /analytics -- usage charts and most-cited sections, all from /admin/stats. */
export function AnalyticsPage() {
  const { data: stats, isLoading, isError, error } = useAdminStats();

  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="6xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Analytics</Heading>

        {isLoading && <Spinner color="brand.500" />}
        {isError && (
          <InlineBanner status="error">{getErrorMessage(error, 'Could not load analytics.')}</InlineBanner>
        )}

        {stats && (
          <>
            <GlassCard>
              <StatsSummary stats={stats} />
            </GlassCard>

            <GlassCard>
              <Heading size="md" mb={4}>
                Query volume
              </Heading>
              <UsageCharts
                codeQueriesPerDay={stats.code_queries_per_day}
                modelQueriesPerDay={stats.model_queries_per_day}
              />
            </GlassCard>

            <GlassCard>
              <Heading size="md" mb={4}>
                Most-cited code sections
              </Heading>
              <CitedSectionsList sections={stats.most_cited_sections} />
            </GlassCard>
          </>
        )}
      </VStack>
    </PageWrapper>
  );
}
