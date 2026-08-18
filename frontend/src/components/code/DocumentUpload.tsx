import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { NativeSelect } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { InlineBanner } from '../ui/InlineBanner';
import { FormStack } from '../ui/FormStack';
import { useUploadCodeDocument } from '../../hooks/useCodeRag';
import type { CodeDocumentSourceType } from '../../types';
import { getErrorMessage } from '../../lib/errors';

const SOURCE_TYPES: CodeDocumentSourceType[] = ['tncdbr', 'municipal_amendment'];

/** Upload form for a new code document, feeding the Code-RAG ingestion pipeline. */
export function DocumentUpload() {
  const upload = useUploadCodeDocument();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [sourceType, setSourceType] = useState<CodeDocumentSourceType>('tncdbr');
  const [jurisdiction, setJurisdiction] = useState('');
  const [version, setVersion] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(false);

    if (!file) {
      setError('Choose a document file to upload.');
      return;
    }

    upload.mutate(
      { file, metadata: { title, source_type: sourceType, jurisdiction, version } },
      {
        onSuccess: () => {
          setSuccess(true);
          setFile(null);
          setTitle('');
          setJurisdiction('');
          setVersion('');
        },
        onError: (err) => setError(getErrorMessage(err, 'Could not upload the document.')),
      },
    );
  };

  return (
    <FormStack onSubmit={handleSubmit} alignItems="stretch" gap={4}>
      {error && <InlineBanner status="error">{error}</InlineBanner>}
      {success && <InlineBanner status="success">Document uploaded for ingestion.</InlineBanner>}

      <AnimatedInput label="Title" required value={title} onChange={(event: ChangeEvent<HTMLInputElement>) => setTitle(event.target.value)} />
      <AnimatedInput
        label="Jurisdiction"
        required
        placeholder="e.g. Chennai Metropolitan Area"
        value={jurisdiction}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setJurisdiction(event.target.value)}
      />
      <AnimatedInput
        label="Version"
        required
        placeholder="e.g. 2019"
        value={version}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setVersion(event.target.value)}
      />

      <NativeSelect.Root>
        <NativeSelect.Field
          value={sourceType}
          onChange={(event: ChangeEvent<HTMLSelectElement>) => setSourceType(event.target.value as CodeDocumentSourceType)}
        >
          {SOURCE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type === 'tncdbr' ? 'TNCDBR' : 'Municipal Amendment'}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>

      <AnimatedInput type="file" accept=".pdf,.doc,.docx,.txt" onChange={handleFileChange} />

      <GradientButton type="submit" isLoading={upload.isPending} alignSelf="flex-start">
        Upload document
      </GradientButton>
    </FormStack>
  );
}
