// Code-RAG API calls (Module 3 in PRPs/revvy-prp.md).
import api from './api';
import type {
  CodeDocument,
  CodeDocumentUploadMetadata,
  CodeRagQueryPayload,
  CodeRagQueryResponse,
} from '../types';

export const codeRagService = {
  async listDocuments(): Promise<CodeDocument[]> {
    const { data } = await api.get<CodeDocument[]>('/code-documents');
    return data;
  },

  async uploadDocument(file: File, metadata: CodeDocumentUploadMetadata): Promise<CodeDocument> {
    const form = new FormData();
    form.append('file', file);
    form.append('title', metadata.title);
    form.append('source_type', metadata.source_type);
    form.append('jurisdiction', metadata.jurisdiction);
    form.append('version', metadata.version);

    const { data } = await api.post<CodeDocument>('/code-documents', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async deleteDocument(documentId: number): Promise<void> {
    await api.delete(`/code-documents/${documentId}`);
  },

  async queryCode(payload: CodeRagQueryPayload): Promise<CodeRagQueryResponse> {
    const { data } = await api.post<CodeRagQueryResponse>('/code-rag/query', payload);
    return data;
  },
};
