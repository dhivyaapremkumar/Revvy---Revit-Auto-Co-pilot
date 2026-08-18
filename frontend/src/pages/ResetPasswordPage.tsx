import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Heading, Text, VStack, Box } from '@chakra-ui/react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { FormStack } from '../components/ui/FormStack';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { InlineBanner } from '../components/ui/InlineBanner';
import { authService } from '../services/authService';
import { getErrorMessage } from '../lib/errors';

/** /reset-password?token=... -- consumes the link from the forgot-password email. */
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await authService.resetPassword({ token, new_password: newPassword });
      setIsSubmitted(true);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not reset your password. The link may have expired.'));
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
            <Heading size="xl">Set a new password</Heading>
            <Text color="gray.600" _dark={{ color: 'gray.300' }} fontSize="sm">
              Choose a new password for your account.
            </Text>
          </VStack>

          {!token ? (
            <InlineBanner status="error">
              This reset link is missing its token. Request a new one from the forgot-password page.
            </InlineBanner>
          ) : isSubmitted ? (
            <InlineBanner status="success">
              Your password has been reset. You can now log in with your new password.
            </InlineBanner>
          ) : (
            <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch">
              {error && <InlineBanner status="error">{error}</InlineBanner>}
              <AnimatedInput
                label="New password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={newPassword}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setNewPassword(event.target.value)}
              />
              <GradientButton type="submit" isLoading={isSubmitting} w="full">
                Reset password
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
