import { useMutation } from '@tanstack/react-query';
import { modelQueryService } from '../services/modelQueryService';
import type { ModelQueryPayload } from '../types';

export function useModelQuery() {
  return useMutation({
    mutationFn: (payload: ModelQueryPayload) => modelQueryService.queryModel(payload),
  });
}
