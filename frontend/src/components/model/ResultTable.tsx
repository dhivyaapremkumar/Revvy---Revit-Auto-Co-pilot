import { Table, Text, VStack } from '@chakra-ui/react';
import type { ModelQueryResult } from '../../types';

export interface ResultTableProps {
  result: ModelQueryResult;
}

/** Renders the read-only model query response: a summary plus per-element parameter table. */
export function ResultTable({ result }: ResultTableProps) {
  const parameterKeys = Array.from(
    new Set(result.elements.flatMap((element) => Object.keys(element.parameters))),
  );

  return (
    <VStack align="stretch" gap={4}>
      <Text fontWeight="medium">{result.result_summary}</Text>

      {result.elements.length === 0 ? (
        <Text color="gray.500" _dark={{ color: 'gray.400' }} fontSize="sm">
          No matching elements were found.
        </Text>
      ) : (
        <Table.ScrollArea>
          <Table.Root size="sm" variant="line">
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeader>Element ID</Table.ColumnHeader>
                <Table.ColumnHeader>Category</Table.ColumnHeader>
                <Table.ColumnHeader>Family</Table.ColumnHeader>
                <Table.ColumnHeader>Type</Table.ColumnHeader>
                {parameterKeys.map((key) => (
                  <Table.ColumnHeader key={key}>{key}</Table.ColumnHeader>
                ))}
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {result.elements.map((element) => (
                <Table.Row key={element.element_id}>
                  <Table.Cell>{element.element_id}</Table.Cell>
                  <Table.Cell>{element.category}</Table.Cell>
                  <Table.Cell>{element.family_name ?? '--'}</Table.Cell>
                  <Table.Cell>{element.type_name ?? '--'}</Table.Cell>
                  {parameterKeys.map((key) => (
                    <Table.Cell key={key}>{String(element.parameters[key] ?? '--')}</Table.Cell>
                  ))}
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        </Table.ScrollArea>
      )}
    </VStack>
  );
}
