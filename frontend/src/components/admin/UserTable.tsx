import { Badge, Table } from '@chakra-ui/react';
import { MotionButton } from '../../lib/motion';
import { useAdminUsers, useUpdateAdminUser } from '../../hooks/useAdmin';

/** Admin table of all users with active/admin toggles. */
export function UserTable() {
  const { data: users, isLoading } = useAdminUsers();
  const updateUser = useUpdateAdminUser();

  if (isLoading || !users) {
    return null;
  }

  return (
    <Table.ScrollArea>
      <Table.Root size="sm" variant="line">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader>Email</Table.ColumnHeader>
            <Table.ColumnHeader>Name</Table.ColumnHeader>
            <Table.ColumnHeader>Status</Table.ColumnHeader>
            <Table.ColumnHeader>Role</Table.ColumnHeader>
            <Table.ColumnHeader>Joined</Table.ColumnHeader>
            <Table.ColumnHeader />
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {users.map((user) => (
            <Table.Row key={user.id}>
              <Table.Cell>{user.email}</Table.Cell>
              <Table.Cell>{user.full_name ?? '--'}</Table.Cell>
              <Table.Cell>
                <Badge colorPalette={user.is_active ? 'green' : 'red'}>
                  {user.is_active ? 'Active' : 'Suspended'}
                </Badge>
              </Table.Cell>
              <Table.Cell>
                <Badge colorPalette={user.is_admin ? 'purple' : 'gray'}>
                  {user.is_admin ? 'Admin' : 'User'}
                </Badge>
              </Table.Cell>
              <Table.Cell>{new Date(user.created_at).toLocaleDateString()}</Table.Cell>
              <Table.Cell textAlign="right">
                <MotionButton
                  type="button"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  fontSize="xs"
                  mr={2}
                  color={user.is_active ? 'red.500' : 'green.600'}
                  bg="transparent"
                  onClick={() =>
                    updateUser.mutate({ userId: user.id, payload: { is_active: !user.is_active } })
                  }
                >
                  {user.is_active ? 'Suspend' : 'Reactivate'}
                </MotionButton>
                <MotionButton
                  type="button"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  fontSize="xs"
                  color="brand.600"
                  bg="transparent"
                  onClick={() =>
                    updateUser.mutate({ userId: user.id, payload: { is_admin: !user.is_admin } })
                  }
                >
                  {user.is_admin ? 'Revoke admin' : 'Make admin'}
                </MotionButton>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Table.ScrollArea>
  );
}
