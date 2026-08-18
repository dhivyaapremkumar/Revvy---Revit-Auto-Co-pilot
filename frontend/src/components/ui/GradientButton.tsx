import type { ReactNode } from 'react';
import type { MotionButtonProps } from '../../lib/motion';
import { MotionButton } from '../../lib/motion';

export interface GradientButtonProps extends Omit<MotionButtonProps, 'children'> {
  children: ReactNode;
  isLoading?: boolean;
}

/**
 * Primary call-to-action button. Use for every primary action per
 * skills/FRONTEND.md UI rules. Always has whileHover/whileTap motion.
 */
export function GradientButton({
  children,
  isLoading = false,
  disabled = false,
  type = 'button',
  ...rest
}: GradientButtonProps) {
  const isDisabled = disabled || isLoading;

  return (
    <MotionButton
      type={type}
      whileHover={isDisabled ? undefined : { scale: 1.03, y: -2 }}
      whileTap={isDisabled ? undefined : { scale: 0.97 }}
      transition={{ duration: 0.15 }}
      display="inline-flex"
      alignItems="center"
      justifyContent="center"
      gap={2}
      px={6}
      py={3}
      borderRadius="full"
      fontWeight="semibold"
      color="white"
      bgGradient="to-r"
      gradientFrom="brand.500"
      gradientTo="accent.500"
      boxShadow="md"
      border="none"
      opacity={isDisabled ? 0.6 : 1}
      cursor={isDisabled ? 'not-allowed' : 'pointer'}
      disabled={isDisabled}
      {...rest}
    >
      {isLoading ? 'Loading...' : children}
    </MotionButton>
  );
}
