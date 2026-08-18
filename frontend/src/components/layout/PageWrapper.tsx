import type { ReactNode } from 'react';
import { MotionBox } from '../../lib/motion';

export interface PageWrapperProps {
  children: ReactNode;
}

/**
 * Wraps every route page so it fades/slides in on mount, per
 * skills/FRONTEND.md UI rules ("EVERY page must fade in using PageWrapper").
 */
export function PageWrapper({ children }: PageWrapperProps) {
  return (
    <MotionBox
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      minH="100vh"
    >
      {children}
    </MotionBox>
  );
}
