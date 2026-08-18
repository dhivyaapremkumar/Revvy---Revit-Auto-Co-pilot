import { Heading, VStack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { NavBar } from '../components/layout/NavBar';
import { GlassCard } from '../components/ui/GlassCard';
import { InlineBanner } from '../components/ui/InlineBanner';
import { QueryForm } from '../components/model/QueryForm';
import { ResultTable } from '../components/model/ResultTable';
import { useModelQuery } from '../hooks/useModelQuery';
import { getErrorMessage } from '../lib/errors';

/** /model-query -- read-only natural-language queries against the open Revit model. */
export function ModelQueryPage() {
  const modelQuery = useModelQuery();

  return (
    <PageWrapper>
      <NavBar />
      <VStack align="stretch" maxW="4xl" mx="auto" px={6} py={8} gap={6}>
        <Heading size="xl">Model Query</Heading>

        <GlassCard>
          <QueryForm onSubmit={(payload) => modelQuery.mutate(payload)} isLoading={modelQuery.isPending} />
        </GlassCard>

        {modelQuery.isError && (
          <InlineBanner status="error">
            {getErrorMessage(modelQuery.error, 'Could not query the open model.')}
          </InlineBanner>
        )}

        {modelQuery.data && (
          <GlassCard>
            <ResultTable result={modelQuery.data} />
          </GlassCard>
        )}
      </VStack>
    </PageWrapper>
  );
}
