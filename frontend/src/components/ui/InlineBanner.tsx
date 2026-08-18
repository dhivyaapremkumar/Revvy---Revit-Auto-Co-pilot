import type { ReactNode } from 'react';
import { Box, Text } from '@chakra-ui/react';

export type InlineBannerStatus = 'error' | 'success' | 'info' | 'warning';

export interface InlineBannerProps {
  status: InlineBannerStatus;
  children: ReactNode;
}

const STATUS_STYLES: Record<InlineBannerStatus, { bg: string; border: string; color: string }> = {
  error: { bg: 'red.50', border: 'red.300', color: 'red.700' },
  success: { bg: 'green.50', border: 'green.300', color: 'green.700' },
  info: { bg: 'brand.50', border: 'brand.300', color: 'brand.700' },
  warning: { bg: 'orange.50', border: 'orange.300', color: 'orange.700' },
};

/**
 * Lightweight status banner for form/page-level feedback (errors, success,
 * warnings). Deliberately built on plain Box rather than Chakra v3's
 * compound Alert primitives to keep the API surface small and predictable.
 */
export function InlineBanner({ status, children }: InlineBannerProps) {
  const styles = STATUS_STYLES[status];
  return (
    <Box
      w="full"
      px={4}
      py={3}
      borderRadius="lg"
      border="1px solid"
      bg={styles.bg}
      borderColor={styles.border}
      _dark={{ bg: 'blackAlpha.400', borderColor: styles.border }}
    >
      <Text fontSize="sm" color={styles.color} _dark={{ color: styles.color }}>
        {children}
      </Text>
    </Box>
  );
}
