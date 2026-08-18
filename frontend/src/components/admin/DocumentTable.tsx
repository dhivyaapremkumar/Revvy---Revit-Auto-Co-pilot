import { Badge, Spinner, Table, Text } from '@chakra-ui/react';
import { useAdminCodeDocuments } from '../../hooks/useAdmin';

/** Admin-facing read view of ingested code documents (management, not upload -- see CodeLibraryPage for upload). */
export function DocumentTable() {
  const { data: documents, isLoading } = useAdminCodeDocuments();

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
    <Table.ScrollArea>
      <Table.Root size="sm" variant="line">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader>Title</Table.ColumnHeader>
            <Table.ColumnHeader>Source</Table.ColumnHeader>
            <Table.ColumnHeader>Jurisdiction</Table.ColumnHeader>
            <Table.ColumnHeader>Version</Table.ColumnHeader>
            <Table.ColumnHeader>Uploaded by</Table.ColumnHeader>
            <Table.ColumnHeader>Ingested</Table.ColumnHeader>
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
              <Table.Cell>{document.uploaded_by}</Table.Cell>
              <Table.Cell>{new Date(document.created_at).toLocaleDateString()}</Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Table.ScrollArea>
  );
}
