// Shared Chakra + Framer Motion primitives.
// Every animated shared component (GlassCard, GradientButton, PageWrapper,
// AnimatedList, AnimatedInput) is built on top of these so animation props
// (whileHover, whileTap, initial, animate, variants, ...) and Chakra style
// props can be used together on the same element.
import type { ComponentProps } from 'react';
import { chakra } from '@chakra-ui/react';
import { isValidMotionProp, motion } from 'framer-motion';
import isPropValid from '@emotion/is-prop-valid';

// `isValidMotionProp` only recognizes Framer Motion's own animation props
// (whileHover, animate, variants, ...) -- it returns false for ordinary DOM
// props/handlers like `onClick`, `disabled`, `type`, `onChange`, `value`.
// Using it alone as `shouldForwardProp` silently drops every standard prop
// that isn't `children`, which breaks click/change handling and disabled
// state on every MotionButton/MotionInput in the app. `isPropValid` covers
// the standard-HTML-attribute half; the two together cover both worlds.
//
// `isPropValid` also accepts a handful of names that are simultaneously
// valid SVG presentation attributes AND the Chakra style props this app
// uses them as (`display`, `color`, `width`, `height`) -- `shouldForwardProp
// -> true` for those makes Chakra forward them as an inert raw DOM
// attribute (`<button display="flex">` does nothing) instead of compiling
// them into the element's style class. That silently dropped every
// `display="flex"` on every MotionButton in the app -- the icon in the New
// Chat tile, the mic/send buttons, the header menu button all rendered as
// block-level with their children left-aligned instead of centered, even
// though `alignItems`/`justifyContent` (not valid attribute names, so never
// hit this path) were compiling correctly right next to it.
const STYLE_ONLY_PROP_NAMES = new Set(['display', 'color', 'width', 'height']);

const shouldForwardProp = (prop: string): boolean =>
  !STYLE_ONLY_PROP_NAMES.has(prop) && (isValidMotionProp(prop) || prop === 'children' || isPropValid(prop));

export const MotionBox = chakra(motion.div, {}, { shouldForwardProp });
const RawMotionButton = chakra(motion.button, {}, { shouldForwardProp });
export const MotionInput = chakra(motion.input, {}, { shouldForwardProp });

// Prop types for the components above, combining Chakra style props with
// Framer Motion animation props (whileHover, initial, variants, ...) --
// use these instead of raw HTMLMotionProps/InputHTMLAttributes so Chakra
// style props (maxW, textAlign, gap, ...) remain assignable.
export type MotionBoxProps = ComponentProps<typeof MotionBox>;
export type MotionButtonProps = ComponentProps<typeof RawMotionButton>;
export type MotionInputProps = ComponentProps<typeof MotionInput>;

// `<button>` carries browser UA-stylesheet padding/appearance that `<a>`
// (used by every `Box asChild` link tile) doesn't -- without resetting it,
// icon-only buttons (mic, send, menu, quick-tool tiles built as buttons)
// render their icon visibly off-center compared to link-based tiles right
// next to them. Defaults here are overridable by any prop the caller passes,
// since `...props` is spread last.
export function MotionButton(props: MotionButtonProps) {
  return (
    <RawMotionButton
      type="button"
      border="none"
      outline="none"
      p={0}
      m={0}
      bg="transparent"
      cursor="pointer"
      css={{ appearance: 'none', WebkitAppearance: 'none', boxSizing: 'border-box', lineHeight: 1 }}
      {...props}
    />
  );
}
