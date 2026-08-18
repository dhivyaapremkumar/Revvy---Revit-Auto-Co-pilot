import { Grid, Stat, Text } from '@chakra-ui/react';
import { GlassCard } from '../ui/GlassCard';
import type { AdminStats } from '../../types';

export interface StatsSummaryProps {
  stats: AdminStats;
}

interface Tile {
  label: string;
  value: string;
}

/** Stat-tile summary of platform usage, shared by AdminDashboardPage and AnalyticsPage. */
export function StatsSummary({ stats }: StatsSummaryProps) {
  const tiles: Tile[] = [
    { label: 'Total users', value: stats.total_users.toLocaleString() },
    { label: 'Active users', value: stats.active_users.toLocaleString() },
    { label: 'Code queries', value: stats.code_queries_total.toLocaleString() },
    { label: 'Model queries', value: stats.model_queries_total.toLocaleString() },
  ];

  return (
    <Grid templateColumns={{ base: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={4}>
      {tiles.map((tile) => (
        <GlassCard key={tile.label} p={4}>
          <Stat.Root>
            <Stat.Label>
              <Text fontSize="xs" color="gray.500" _dark={{ color: 'gray.400' }}>
                {tile.label}
              </Text>
            </Stat.Label>
            <Stat.ValueText fontSize="2xl" fontWeight="bold">
              {tile.value}
            </Stat.ValueText>
          </Stat.Root>
        </GlassCard>
      ))}
    </Grid>
  );
}
