import { Box, HStack, Text, VStack } from '@chakra-ui/react';
import type { DailyCount } from '../../types';

export interface UsageChartsProps {
  codeQueriesPerDay: DailyCount[];
  modelQueriesPerDay: DailyCount[];
}

function DailySeries({ label, colorScale, series }: { label: string; colorScale: string; series: DailyCount[] }) {
  if (series.length === 0) {
    return (
      <VStack align="stretch" gap={1}>
        <Text fontSize="sm" fontWeight="medium">
          {label}
        </Text>
        <Text color="gray.500" _dark={{ color: 'gray.400' }} fontSize="sm">
          No activity recorded yet.
        </Text>
      </VStack>
    );
  }

  const maxCount = Math.max(...series.map((point) => point.count), 1);

  return (
    <VStack align="stretch" gap={2}>
      <Text fontSize="sm" fontWeight="medium">
        {label}
      </Text>
      <HStack align="flex-end" gap={1} h="80px">
        {series.map((point) => (
          <Box
            key={point.date}
            flex="1"
            h={`${Math.max((point.count / maxCount) * 100, 4)}%`}
            bg={colorScale}
            borderRadius="sm"
            title={`${point.date}: ${point.count}`}
          />
        ))}
      </HStack>
    </VStack>
  );
}

/** Daily query-volume bar charts (Code-RAG vs. Model Query), sourced from GET /admin/stats. */
export function UsageCharts({ codeQueriesPerDay, modelQueriesPerDay }: UsageChartsProps) {
  return (
    <VStack align="stretch" gap={6}>
      <DailySeries label="Code-RAG queries / day" colorScale="brand.500" series={codeQueriesPerDay} />
      <DailySeries label="Model queries / day" colorScale="accent.500" series={modelQueriesPerDay} />
    </VStack>
  );
}
