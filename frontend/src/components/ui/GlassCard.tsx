import type { ReactNode } from 'react';
import type { MotionBoxProps } from '../../lib/motion';
import { MotionBox } from '../../lib/motion';

export interface GlassCardProps extends Omit<MotionBoxProps, 'children'> {
  children: ReactNode;
}

/**
 * Frosted-glass card container. Use for every card-shaped container per
 * skills/FRONTEND.md UI rules. Fades/rises in on mount and lifts on hover.
 */
export function GlassCard({ children, ...rest }: GlassCardProps) {
  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -6, scale: 1.01 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      p={6}
      borderRadius="2xl"
      bg="whiteAlpha.700"
      backdropFilter="blur(16px)"
      border="1px solid"
      borderColor="whiteAlpha.400"
      boxShadow="xl"
      _dark={{ bg: 'blackAlpha.400', borderColor: 'whiteAlpha.100' }}
      {...rest}
    >
      {children}
    </MotionBox>
  );
}
