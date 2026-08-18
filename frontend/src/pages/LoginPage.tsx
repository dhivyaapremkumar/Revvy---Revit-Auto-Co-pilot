import { Heading, Text, VStack } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { Box } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { LoginForm } from '../components/auth/LoginForm';

export function LoginPage() {
  return (
    <PageWrapper>
      <MeshBackground />
      <VStack minH="100vh" justify="center" px={6} gap={6}>
        <GlassCard maxW="md" w="full">
          <VStack gap={1} mb={6} align="center">
            <Heading size="xl">Welcome back</Heading>
            <Text color="gray.600" _dark={{ color: 'gray.300' }} fontSize="sm">
              Log in to your REVVY account
            </Text>
          </VStack>
          <LoginForm />
          <VStack gap={2} mt={5}>
            <Box asChild fontSize="sm" color="brand.600" _dark={{ color: 'brand.300' }}>
              <RouterLink to="/forgot-password">Forgot your password?</RouterLink>
            </Box>
            <Text fontSize="sm" color="gray.600" _dark={{ color: 'gray.300' }}>
              No account yet?{' '}
              <Box asChild display="inline" color="brand.600" fontWeight="semibold" _dark={{ color: 'brand.300' }}>
                <RouterLink to="/register">Sign up</RouterLink>
              </Box>
            </Text>
          </VStack>
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
