import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { FormStack } from '../ui/FormStack';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import type { ModelQueryPayload } from '../../types';

export interface QueryFormProps {
  onSubmit: (payload: ModelQueryPayload) => void;
  isLoading?: boolean;
}

export function QueryForm({ onSubmit, isLoading = false }: QueryFormProps) {
  const [revitProjectName, setRevitProjectName] = useState('');
  const [query, setQuery] = useState('');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!revitProjectName.trim() || !query.trim()) {
      return;
    }
    onSubmit({ revit_project_name: revitProjectName.trim(), query: query.trim() });
  };

  return (
    <FormStack onSubmit={handleSubmit} gap={4} alignItems="stretch">
      <AnimatedInput
        label="Revit project"
        placeholder="e.g. Chennai-Residence-01.rvt"
        required
        value={revitProjectName}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setRevitProjectName(event.target.value)}
      />
      <AnimatedInput
        label="Query"
        placeholder="e.g. List all doors on Level 1 wider than 900mm"
        required
        value={query}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
      />
      <GradientButton type="submit" isLoading={isLoading} alignSelf="flex-start">
        Run query
      </GradientButton>
    </FormStack>
  );
}
