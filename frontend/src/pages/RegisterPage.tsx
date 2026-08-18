import { Heading, Text, VStack, Box } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { RegisterForm } from '../components/auth/RegisterForm';

export function RegisterPage() {
  return (
    <PageWrapper>
      <MeshBackground />
      <VStack minH="100vh" justify="center" px={6} gap={6}>
        <GlassCard maxW="md" w="full">
          <VStack gap={1} mb={6} align="center">
            <Heading size="xl">Create your account</Heading>
            <Text color="gray.600" _dark={{ color: 'gray.300' }} fontSize="sm">
              Start using REVVY's AI copilot for Revit
            </Text>
          </VStack>
          <RegisterForm />
          <Text fontSize="sm" color="gray.600" mt={5} textAlign="center" _dark={{ color: 'gray.300' }}>
            Already have an account?{' '}
            <Box asChild display="inline" color="brand.600" fontWeight="semibold" _dark={{ color: 'brand.300' }}>
              <RouterLink to="/login">Log in</RouterLink>
            </Box>
          </Text>
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
