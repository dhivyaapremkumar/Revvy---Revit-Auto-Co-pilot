import { chakra } from '@chakra-ui/react';

/**
 * A `<form>` styled like VStack/HStack (flex column by default). Chakra v3's
 * `as="form"` prop on Box/VStack keeps the base component's event-handler
 * types (HTMLDivElement), which breaks `onSubmit={(e: FormEvent<HTMLFormElement>) => ...}`
 * under strict TS -- use this instead so `onSubmit` is correctly typed
 * against a real `<form>` element.
 */
export const FormStack = chakra('form', {
  base: {
    display: 'flex',
    flexDirection: 'column',
  },
});
