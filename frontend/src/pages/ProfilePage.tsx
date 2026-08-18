import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Badge, Heading, HStack, Text, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { FormStack } from '../components/ui/FormStack';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { InlineBanner } from '../components/ui/InlineBanner';
import { useAuth } from '../hooks/useAuth';
import { getErrorMessage } from '../lib/errors';

export function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);
    try {
      await updateProfile({ full_name: fullName });
      setSuccess(true);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not update your profile.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="2xl" mx="auto" px={6} py={10} gap={6}>
        <Heading size="xl">Your profile</Heading>

        <GlassCard>
          <VStack align="stretch" gap={4}>
            <HStack justify="space-between">
              <Text color="gray.600" _dark={{ color: 'gray.300' }}>
                {user.email}
              </Text>
              <HStack gap={2}>
                <Badge colorPalette={user.is_verified ? 'green' : 'orange'}>
                  {user.is_verified ? 'Verified' : 'Unverified'}
                </Badge>
                {user.is_admin && <Badge colorPalette="purple">Admin</Badge>}
              </HStack>
            </HStack>

            {error && <InlineBanner status="error">{error}</InlineBanner>}
            {success && <InlineBanner status="success">Profile updated.</InlineBanner>}

            <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch">
              <AnimatedInput
                label="Full name"
                value={fullName}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setFullName(event.target.value)}
              />
              <GradientButton type="submit" isLoading={isSubmitting} alignSelf="flex-start">
                Save changes
              </GradientButton>
            </FormStack>
          </VStack>
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
