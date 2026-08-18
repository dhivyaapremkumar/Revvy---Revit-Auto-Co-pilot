import { Box } from '@chakra-ui/react';

/**
 * Soft gradient-mesh backdrop. Add to landing/auth pages per
 * skills/FRONTEND.md UI rules. Purely decorative -- render behind content
 * with position="fixed" and no pointer events.
 */
export function MeshBackground() {
  return (
    <Box
      position="fixed"
      inset={0}
      zIndex={-1}
      overflow="hidden"
      pointerEvents="none"
      aria-hidden="true"
    >
      <Box
        position="absolute"
        inset={0}
        bgGradient="to-br"
        gradientFrom="brand.50"
        gradientTo="accent.50"
        _dark={{ gradientFrom: 'gray.900', gradientTo: 'brand.900' }}
      />
      <Box
        position="absolute"
        top="-10%"
        left="8%"
        w="420px"
        h="420px"
        borderRadius="full"
        bg="brand.300"
        opacity={0.35}
        filter="blur(90px)"
      />
      <Box
        position="absolute"
        bottom="-10%"
        right="8%"
        w="420px"
        h="420px"
        borderRadius="full"
        bg="accent.300"
        opacity={0.35}
        filter="blur(90px)"
      />
    </Box>
  );
}
