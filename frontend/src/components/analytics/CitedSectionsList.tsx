import { Box, HStack, Text, VStack } from '@chakra-ui/react';
import type { CitedSectionStat } from '../../types';

export interface CitedSectionsListProps {
  sections: CitedSectionStat[];
}

/**
 * Ranked horizontal-bar list of the most-cited TNCDBR sections. A single
 * brand hue encodes citation count (magnitude), bar length is the mark,
 * count is direct-labeled since this is a short leaderboard, not a dense
 * series.
 */
export function CitedSectionsList({ sections }: CitedSectionsListProps) {
  if (sections.length === 0) {
    return (
      <Text color="gray.500" _dark={{ color: 'gray.400' }} fontSize="sm">
        No code sections have been cited yet.
      </Text>
    );
  }

  const maxCount = Math.max(...sections.map((section) => section.count));

  return (
    <VStack align="stretch" gap={3}>
      {sections.map((section) => (
        <VStack key={`${section.document_title}-${section.section_reference}`} align="stretch" gap={1}>
          <HStack justify="space-between">
            <Text fontSize="sm" fontWeight="medium">
              {section.section_reference}
              <Text as="span" fontSize="xs" color="gray.500" _dark={{ color: 'gray.400' }}>
                {' '}
                -- {section.document_title}
              </Text>
            </Text>
            <Text fontSize="sm" fontWeight="semibold" color="brand.600" _dark={{ color: 'brand.300' }}>
              {section.count}
            </Text>
          </HStack>
          <Box
            h="8px"
            w="full"
            borderRadius="full"
            bg="brand.100"
            _dark={{ bg: 'whiteAlpha.200' }}
            overflow="hidden"
            title={`${section.count} citations`}
          >
            <Box
              h="full"
              borderRadius="full"
              bg="brand.500"
              w={`${Math.max((section.count / maxCount) * 100, 4)}%`}
            />
          </Box>
        </VStack>
      ))}
    </VStack>
  );
}
