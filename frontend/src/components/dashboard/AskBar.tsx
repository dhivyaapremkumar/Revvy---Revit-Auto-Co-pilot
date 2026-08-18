import { useState } from 'react';
import { Box, HStack, Text } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { MotionInput, MotionButton } from '../../lib/motion';
import { MicIcon, SendIcon } from './icons';
import { useAskRevvy } from '../../hooks/useChat';
import { useSpeechInput } from '../../hooks/useSpeechInput';
import { InlineBanner } from '../ui/InlineBanner';
import { getErrorMessage } from '../../lib/errors';

export interface AskBarModule {
  label: string;
  to: string;
}

export interface AskBarProps {
  /** Real REVVY modules, used to route spoken navigation commands ("open model query") to the right page. */
  modules: AskBarModule[];
  /** True when running inside the voice agent's pywebview window (see usePywebviewBridge). */
  isEmbedded?: boolean;
}

const NAV_VERBS = ['open', 'go to', 'navigate to', 'show me', 'take me to', 'switch to'];

/** "open model query" -> /model-query. Returns null if `transcript` doesn't read as a navigation command. */
function matchNavigation(transcript: string, modules: AskBarModule[]): string | null {
  const lower = transcript.toLowerCase().trim();
  if (!NAV_VERBS.some((verb) => lower.startsWith(verb))) return null;

  for (const m of modules) {
    const keywords = m.label
      .toLowerCase()
      .split(' ')
      .filter((word) => word.length > 3 && word !== 'panel');
    if (keywords.some((keyword) => lower.includes(keyword))) return m.to;
  }
  return null;
}

/** The "Ask REVVY anything" bar -- creates a real chat session + sends the first message. */
export function AskBar({ modules, isEmbedded = false }: AskBarProps) {
  const [question, setQuestion] = useState('');
  const navigate = useNavigate();
  const askRevvy = useAskRevvy();

  const handleSubmit = async (overrideText?: string) => {
    const trimmed = (overrideText ?? question).trim();
    if (!trimmed) return;

    const destination = matchNavigation(trimmed, modules);
    if (destination) {
      setQuestion('');
      navigate(destination);
      return;
    }

    // Embedded in the voice agent's own window -- hand off to the real
    // agent (RevitMCP tools, actually acts on the model) instead of the
    // web-only chat backend. Its reply arrives asynchronously via the
    // pywebview bridge (see usePywebviewBridge), not as an HTTP response,
    // so there's no session to navigate to here.
    if (isEmbedded && window.pywebview) {
      window.pywebview.api.submit_text(trimmed);
      setQuestion('');
      return;
    }

    if (askRevvy.isPending) return;
    const session = await askRevvy.mutateAsync(trimmed);
    navigate(`/chat/${session.id}`);
  };

  const speech = useSpeechInput((transcript) => {
    setQuestion(transcript);
    void handleSubmit(transcript);
  });

  return (
    <Box w="full" maxW="3xl" mx="auto">
      {askRevvy.isError && (
        <Box mb={3}>
          <InlineBanner status="error">
            {getErrorMessage(askRevvy.error, 'Could not start a chat with REVVY.')}
          </InlineBanner>
        </Box>
      )}
      <HStack
        w="full"
        bg="whiteAlpha.100"
        border="1px solid"
        borderColor="cyan.700"
        borderRadius="full"
        px={4}
        py={2}
        gap={2}
        backdropFilter="blur(12px)"
        boxShadow="0 0 30px rgba(56,224,255,0.08)"
      >
        <MotionInput
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void handleSubmit();
            }
          }}
          placeholder={
            isEmbedded ? 'Type a question, or just say "hey jarvis"...' : 'Ask REVVY anything... e.g. Check egress for floor 1'
          }
          bg="transparent"
          border="none"
          outline="none"
          color="whiteAlpha.900"
          fontSize="sm"
          flex={1}
          _placeholder={{ color: 'whiteAlpha.500' }}
          whileFocus={{ scale: 1.005 }}
        />
        {!isEmbedded && speech.isSupported && (
          <MotionButton
            type="button"
            aria-label={speech.isListening ? 'Stop dictation' : 'Start dictation'}
            onClick={() => (speech.isListening ? speech.stop() : speech.start())}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            display="flex"
            alignItems="center"
            justifyContent="center"
            w="34px"
            h="34px"
            borderRadius="full"
            bg={speech.isListening ? 'red.500' : 'whiteAlpha.100'}
            color={speech.isListening ? 'white' : 'cyan.300'}
            border="1px solid"
            borderColor={speech.isListening ? 'red.400' : 'cyan.700'}
          >
            <MicIcon size={18} />
          </MotionButton>
        )}
        <MotionButton
          type="button"
          aria-label="Send"
          onClick={() => void handleSubmit()}
          disabled={askRevvy.isPending || !question.trim()}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.94 }}
          display="flex"
          alignItems="center"
          justifyContent="center"
          w="34px"
          h="34px"
          borderRadius="full"
          bg="cyan.400"
          color="gray.950"
          border="none"
          opacity={askRevvy.isPending || !question.trim() ? 0.5 : 1}
          cursor={askRevvy.isPending || !question.trim() ? 'not-allowed' : 'pointer'}
        >
          <SendIcon size={18} />
        </MotionButton>
      </HStack>
      {speech.isListening && (
        <Text mt={2} fontSize="xs" color="cyan.300" textAlign="center">
          Listening... ask a question, or say "open [module name]" to navigate.
        </Text>
      )}
    </Box>
  );
}
