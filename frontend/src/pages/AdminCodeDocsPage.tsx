import { Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { DocumentTable } from '../components/admin/DocumentTable';

/** /admin/code-documents -- admin oversight of code document ingestion. */
export function AdminCodeDocsPage() {
  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="6xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Code Documents</Heading>
        <GlassCard>
          <DocumentTable />
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
