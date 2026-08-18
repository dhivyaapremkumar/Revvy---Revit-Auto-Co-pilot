import { Box, Heading, Text, VStack } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { OrbVisual } from './OrbVisual';
import { GradientButton } from '../ui/GradientButton';

/** Landing hero shown to signed-out visitors on "/" -- no user data to show yet. */
export function GuestHero() {
  const navigate = useNavigate();

  return (
    <Box minH="100vh" bg="gray.950" color="whiteAlpha.900" position="relative" overflow="hidden">
      <Box
        position="absolute"
        inset={0}
        bgGradient="to-b"
        gradientFrom="gray.950"
        gradientTo="blue.950"
        zIndex={0}
      />
      <VStack minH="100vh" justify="center" gap={8} px={6} position="relative" zIndex={1}>
        <OrbVisual size={260} />
        <VStack gap={2} textAlign="center">
          <Heading size="3xl" letterSpacing="widest" color="whiteAlpha.900">
            REVVY
          </Heading>
          <Text fontSize="sm" letterSpacing="widest" color="cyan.300" textTransform="uppercase">
            Your AI Revit Copilot
          </Text>
        </VStack>
        <Text maxW="lg" textAlign="center" color="whiteAlpha.700">
          Chat, code-cited Tamil Nadu Building Code answers, and Revit model
          queries -- grounded in your ingested code and your open model, never
          guessed.
        </Text>
        <GradientButton onClick={() => navigate('/login')}>Get Started</GradientButton>
      </VStack>
    </Box>
  );
}
