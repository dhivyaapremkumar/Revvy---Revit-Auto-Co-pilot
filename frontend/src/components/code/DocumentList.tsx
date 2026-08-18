import { Badge, Spinner, Table, Text } from '@chakra-ui/react';
import { MotionButton } from '../../lib/motion';
import { useCodeDocuments, useDeleteCodeDocument } from '../../hooks/useCodeRag';

/** Table of ingested code documents, with delete controls. */
export function DocumentList() {
  const { data: documents, isLoading } = useCodeDocuments();
  const deleteDocument = useDeleteCodeDocument();

  if (isLoading) {
    return <Spinner color="brand.500" />;
  }

  if (!documents || documents.length === 0) {
    return (
      <Text color="gray.500" _dark={{ color: 'gray.400' }} fontSize="sm">
        No code documents ingested yet.
      </Text>
    );
  }

  return (
    <Table.Root size="sm" variant="line">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>Title</Table.ColumnHeader>
          <Table.ColumnHeader>Source</Table.ColumnHeader>
          <Table.ColumnHeader>Jurisdiction</Table.ColumnHeader>
          <Table.ColumnHeader>Version</Table.ColumnHeader>
          <Table.ColumnHeader />
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {documents.map((document) => (
          <Table.Row key={document.id}>
            <Table.Cell>{document.title}</Table.Cell>
            <Table.Cell>
              <Badge colorPalette={document.source_type === 'tncdbr' ? 'purple' : 'blue'}>
                {document.source_type}
              </Badge>
            </Table.Cell>
            <Table.Cell>{document.jurisdiction}</Table.Cell>
            <Table.Cell>{document.version}</Table.Cell>
            <Table.Cell textAlign="right">
              <MotionButton
                type="button"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                fontSize="xs"
                color="red.500"
                bg="transparent"
                onClick={() => deleteDocument.mutate(document.id)}
              >
                Remove
              </MotionButton>
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}
