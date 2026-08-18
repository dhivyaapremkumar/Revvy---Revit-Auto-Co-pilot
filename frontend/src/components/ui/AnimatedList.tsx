import type { ReactNode } from 'react';
import { MotionBox } from '../../lib/motion';

export interface AnimatedListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  getKey: (item: T, index: number) => string | number;
  emptyState?: ReactNode;
}

/**
 * Stagger-animated list. Use for every list of items per
 * skills/FRONTEND.md UI rules (chat sessions, code documents, users, ...).
 * Generic over the item type so callers never need `any`.
 */
export function AnimatedList<T>({ items, renderItem, getKey, emptyState }: AnimatedListProps<T>) {
  if (items.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <MotionBox
      initial="hidden"
      animate="visible"
      variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
      display="flex"
      flexDirection="column"
      gap={3}
    >
      {items.map((item, index) => (
        <MotionBox
          key={getKey(item, index)}
          variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }}
        >
          {renderItem(item, index)}
        </MotionBox>
      ))}
    </MotionBox>
  );
}
