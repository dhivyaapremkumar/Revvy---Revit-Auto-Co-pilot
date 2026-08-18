import { forwardRef } from 'react';
import { Box, Text } from '@chakra-ui/react';
import type { MotionInputProps } from '../../lib/motion';
import { MotionInput } from '../../lib/motion';

export interface AnimatedInputProps extends MotionInputProps {
  label?: string;
  error?: string;
}

/**
 * Form input with a focus animation. Use for every form input per
 * skills/FRONTEND.md UI rules.
 */
export const AnimatedInput = forwardRef<HTMLInputElement, AnimatedInputProps>(
  ({ label, error, ...rest }, ref) => (
    <Box w="full">
      {label && (
        <Text as="label" display="block" mb={1} fontSize="sm" fontWeight="medium">
          {label}
        </Text>
      )}
      <MotionInput
        ref={ref}
        whileFocus={{ scale: 1.01 }}
        transition={{ duration: 0.15 }}
        w="full"
        px={4}
        py={3}
        borderRadius="xl"
        border="2px solid"
        borderColor={error ? 'red.500' : 'gray.200'}
        bg="transparent"
        outline="none"
        _focus={{ borderColor: error ? 'red.500' : 'brand.500' }}
        _dark={{ borderColor: error ? 'red.400' : 'gray.700' }}
        {...rest}
      />
      {error && (
        <Text color="red.500" fontSize="sm" mt={1}>
          {error}
        </Text>
      )}
    </Box>
  ),
);

AnimatedInput.displayName = 'AnimatedInput';
