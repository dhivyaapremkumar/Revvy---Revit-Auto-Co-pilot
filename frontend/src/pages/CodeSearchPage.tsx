import { Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { InlineBanner } from '../components/ui/InlineBanner';
import { SearchBar } from '../components/code/SearchBar';
import { CitedAnswer } from '../components/code/CitedAnswer';
import { useCodeRagQuery } from '../hooks/useCodeRag';
import { getErrorMessage } from '../lib/errors';

/** /code-search -- ask TNCDBR compliance questions, see cited answers. */
export function CodeSearchPage() {
  const codeQuery = useCodeRagQuery();

  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="3xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Code Search</Heading>

        <GlassCard>
          <SearchBar onSearch={(query) => codeQuery.mutate({ query })} isLoading={codeQuery.isPending} />
        </GlassCard>

        {codeQuery.isError && (
          <InlineBanner status="error">
            {getErrorMessage(codeQuery.error, 'Could not search the building code.')}
          </InlineBanner>
        )}

        {codeQuery.data && <CitedAnswer result={codeQuery.data} />}
      </VStack>
    </PageWrapper>
  );
}
