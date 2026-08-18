import { Badge, Heading, Text, VStack } from '@chakra-ui/react';
import { AnimatedList } from '../ui/AnimatedList';
import { GlassCard } from '../ui/GlassCard';
import type { CodeChunkCitation, CodeRagQueryResponse } from '../../types';

export interface CitedAnswerProps {
  result: CodeRagQueryResponse;
}

/** Cited RAG answer -- the answer text plus every code-section citation it draws on. */
export function CitedAnswer({ result }: CitedAnswerProps) {
  return (
    <VStack align="stretch" gap={4}>
      <GlassCard>
        <Text whiteSpace="pre-wrap">{result.answer}</Text>
      </GlassCard>

      <Heading size="sm">Cited sections ({result.cited_chunks.length})</Heading>
      <AnimatedList<CodeChunkCitation>
        items={result.cited_chunks}
        getKey={(citation) => citation.chunk_id}
        emptyState={
          <Text fontSize="sm" color="gray.500" _dark={{ color: 'gray.400' }}>
            No citations were found for this answer.
          </Text>
        }
        renderItem={(citation) => (
          <GlassCard p={4}>
            <VStack align="stretch" gap={2}>
              <VStack align="stretch" gap={1}>
                <Badge colorPalette="purple" alignSelf="flex-start">
                  {citation.section_reference}
                </Badge>
                <Text fontSize="xs" color="gray.500" _dark={{ color: 'gray.400' }}>
                  {citation.document_title}
                  {typeof citation.similarity_score === 'number'
                    ? ` -- match ${(citation.similarity_score * 100).toFixed(0)}%`
                    : ''}
                </Text>
              </VStack>
              <Text fontSize="sm">{citation.content}</Text>
            </VStack>
          </GlassCard>
        )}
      />
    </VStack>
  );
}
