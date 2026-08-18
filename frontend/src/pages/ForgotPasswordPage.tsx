import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Heading, Text, VStack, Box } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { FormStack } from '../components/ui/FormStack';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { InlineBanner } from '../components/ui/InlineBanner';
import { authService } from '../services/authService';
import { getErrorMessage } from '../lib/errors';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await authService.forgotPassword({ email });
      setIsSubmitted(true);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not send a reset email.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper>
      <MeshBackground />
      <VStack minH="100vh" justify="center" px={6} gap={6}>
        <GlassCard maxW="md" w="full">
          <VStack gap={1} mb={6} align="center">
            <Heading size="xl">Reset your password</Heading>
            <Text color="gray.600" _dark={{ color: 'gray.300' }} fontSize="sm">
              We'll email you a link to reset your password.
            </Text>
          </VStack>

          {isSubmitted ? (
            <InlineBanner status="success">
              If an account exists for {email}, a reset link is on its way.
            </InlineBanner>
          ) : (
            <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch">
              {error && <InlineBanner status="error">{error}</InlineBanner>}
              <AnimatedInput
                label="Email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setEmail(event.target.value)}
              />
              <GradientButton type="submit" isLoading={isSubmitting} w="full">
                Send reset link
              </GradientButton>
            </FormStack>
          )}

          <Text fontSize="sm" color="gray.600" mt={5} textAlign="center" _dark={{ color: 'gray.300' }}>
            <Box asChild display="inline" color="brand.600" fontWeight="semibold" _dark={{ color: 'brand.300' }}>
              <RouterLink to="/login">Back to log in</RouterLink>
            </Box>
          </Text>
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
