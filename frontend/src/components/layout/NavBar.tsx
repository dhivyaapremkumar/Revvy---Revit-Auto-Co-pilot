import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, Flex, HStack } from '@chakra-ui/react';
import { useAuth } from '../../hooks/useAuth';
import { MotionButton } from '../../lib/motion';

interface NavLinkItem {
  to: string;
  label: string;
  adminOnly?: boolean;
}

const NAV_LINKS: NavLinkItem[] = [
  { to: '/chat', label: 'Chat' },
  { to: '/code-search', label: 'Code Search' },
  { to: '/code-library', label: 'Code Library' },
  { to: '/model-query', label: 'Model Query' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/admin', label: 'Admin', adminOnly: true },
];

/**
 * Top nav for every authenticated page, so Phase 2's modules are reachable
 * from one another instead of only by typing a URL. Rendered by each
 * protected page rather than globally, so unauthenticated pages (login,
 * register, the landing page) stay nav-free.
 */
export function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    void logout().then(() => navigate('/login'));
  };

  return (
    <Flex
      as="nav"
      w="full"
      px={6}
      py={3}
      align="center"
      justify="space-between"
      borderBottom="1px solid"
      borderColor="blackAlpha.100"
      bg="whiteAlpha.800"
      backdropFilter="blur(12px)"
      position="sticky"
      top={0}
      zIndex={10}
      _dark={{ bg: 'blackAlpha.500', borderColor: 'whiteAlpha.100' }}
    >
      <HStack gap={5} overflowX="auto">
        <Box asChild fontWeight="bold" color="brand.600" _dark={{ color: 'brand.300' }} whiteSpace="nowrap" _hover={{ opacity: 0.8 }}>
          <RouterLink to="/">REVVY</RouterLink>
        </Box>
        {NAV_LINKS.filter((link) => !link.adminOnly || user?.is_admin).map((link) => (
          <Box
            key={link.to}
            asChild
            fontSize="sm"
            fontWeight="medium"
            color="gray.600"
            whiteSpace="nowrap"
            _hover={{ color: 'brand.600' }}
            _dark={{ color: 'gray.300' }}
          >
            <RouterLink to={link.to}>{link.label}</RouterLink>
          </Box>
        ))}
      </HStack>
      <HStack gap={3}>
        <Box asChild fontSize="sm" color="gray.500" _dark={{ color: 'gray.400' }}>
          <RouterLink to="/profile">{user?.email}</RouterLink>
        </Box>
        <MotionButton
          type="button"
          onClick={handleLogout}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          px={4}
          py={2}
          borderRadius="full"
          fontSize="sm"
          fontWeight="semibold"
          border="1px solid"
          borderColor="brand.300"
          color="brand.600"
          bg="transparent"
          _dark={{ color: 'brand.300', borderColor: 'brand.700' }}
        >
          Log out
        </MotionButton>
      </HStack>
    </Flex>
  );
}
