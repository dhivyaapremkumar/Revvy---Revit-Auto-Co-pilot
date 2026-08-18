import { Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { DocumentUpload } from '../components/code/DocumentUpload';
import { DocumentList } from '../components/code/DocumentList';

/** /code-library -- upload + manage ingested TNCDBR / amendment documents. */
export function CodeLibraryPage() {
  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="4xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Code Library</Heading>

        <GlassCard>
          <Heading size="md" mb={4}>
            Upload a document
          </Heading>
          <DocumentUpload />
        </GlassCard>

        <GlassCard>
          <Heading size="md" mb={4}>
            Ingested documents
          </Heading>
          <DocumentList />
        </GlassCard>
      </VStack>
    </PageWrapper>
  );
}
