import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { FormStack } from '../ui/FormStack';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';

export interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchBar({ onSearch, isLoading = false }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      onSearch(trimmed);
    }
  };

  return (
    <FormStack onSubmit={handleSubmit} flexDirection="row" gap={3} alignItems="flex-start" w="full">
      <AnimatedInput
        placeholder="Ask a TNCDBR compliance question..."
        value={query}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
      />
      <GradientButton type="submit" isLoading={isLoading}>
        Search
      </GradientButton>
    </FormStack>
  );
}
