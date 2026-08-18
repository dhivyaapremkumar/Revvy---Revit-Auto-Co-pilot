import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { codeRagService } from '../services/codeRagService';
import type { CodeDocumentUploadMetadata, CodeRagQueryPayload } from '../types';

const DOCUMENTS_KEY = ['code-documents'] as const;

export function useCodeDocuments() {
  return useQuery({ queryKey: DOCUMENTS_KEY, queryFn: codeRagService.listDocuments });
}

export function useUploadCodeDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, metadata }: { file: File; metadata: CodeDocumentUploadMetadata }) =>
      codeRagService.uploadDocument(file, metadata),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

export function useDeleteCodeDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: number) => codeRagService.deleteDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

export function useCodeRagQuery() {
  return useMutation({
    mutationFn: (payload: CodeRagQueryPayload) => codeRagService.queryCode(payload),
  });
}
