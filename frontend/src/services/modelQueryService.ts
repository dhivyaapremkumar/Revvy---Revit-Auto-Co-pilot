// Model Query API calls (Module 4 in PRPs/revvy-prp.md).
import api from './api';
import type { ModelQueryPayload, ModelQueryResult } from '../types';

export const modelQueryService = {
  async queryModel(payload: ModelQueryPayload): Promise<ModelQueryResult> {
    const { data } = await api.post<ModelQueryResult>('/model/query', payload);
    return data;
  },
};
