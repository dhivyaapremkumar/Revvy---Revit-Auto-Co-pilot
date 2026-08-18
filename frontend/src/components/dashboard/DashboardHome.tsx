import { useMemo, useState } from 'react';
import type { ComponentType } from 'react';
import { Box, Grid, GridItem, HStack, Heading, Text, VStack } from '@chakra-ui/react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useChatSessions, useCreateChatSession } from '../../hooks/useChat';
import { useVoiceAgentBridge } from '../../context/VoiceAgentBridgeContext';
import { OrbVisual } from './OrbVisual';
import { ModuleOrbit } from './ModuleOrbit';
import { AskBar } from './AskBar';
import { AnimatedList } from '../ui/AnimatedList';
import { MotionBox, MotionButton } from '../../lib/motion';
import type { DashboardIconProps } from './icons';
import {
  ChatIcon,
  ShieldCheckIcon,
  CubeIcon,
  ChartIcon,
  BookIcon,
  UsersIcon,
  PlusIcon,
  ChevronRightIcon,
  MenuIcon,
  ClockIcon,
  MicIcon,
} from './icons';

interface ModuleItem {
  key: string;
  label: string;
  description: string;
  to: string;
  Icon: ComponentType<DashboardIconProps>;
  adminOnly?: boolean;
}

type QuickAction =
  | { key: string; label: string; Icon: ComponentType<DashboardIconProps>; to: string }
  | { key: string; label: string; Icon: ComponentType<DashboardIconProps>; onClick: () => void };

const MODULES: ModuleItem[] = [
  { key: 'chat', label: 'Chat Copilot', description: 'Ask REVVY about your Revit workflow', to: '/chat', Icon: ChatIcon },
  {
    key: 'code',
    label: 'Code Compliance',
    description: 'Cited answers from Tamil Nadu Building Code',
    to: '/code-search',
    Icon: ShieldCheckIcon,
  },
  {
    key: 'library',
    label: 'Code Library',
    description: 'Manage ingested TNCDBR documents',
    to: '/code-library',
    Icon: BookIcon,
    adminOnly: true,
  },
  { key: 'model', label: 'Model Query', description: 'Query the open Revit model', to: '/model-query', Icon: CubeIcon },
  {
    key: 'analytics',
    label: 'Analytics',
    description: 'Usage & most-cited code sections',
    to: '/analytics',
    Icon: ChartIcon,
  },
  {
    key: 'admin',
    label: 'Admin Panel',
    description: 'Manage users & platform stats',
    to: '/admin',
    Icon: UsersIcon,
    adminOnly: true,
  },
];

const tileStyle = {
  display: 'flex' as const,
  flexDirection: 'column' as const,
  alignItems: 'center',
  justifyContent: 'center',
  // Grid's implicit stretch doesn't apply to <button> the way it does to
  // <a> (Box asChild) -- without this the New Chat tile shrinks to fit its
  // content and its icon reads as left-aligned next to the other tiles.
  // Both props set belt-and-braces (one engine honoring w:'full' without
  // also fully honoring justifySelf has been observed).
  w: 'full',
  justifySelf: 'stretch' as const,
  borderRadius: 'xl',
  border: '1px solid',
  borderColor: 'whiteAlpha.100',
  bg: 'whiteAlpha.50',
  cursor: 'pointer',
  py: 3,
  gap: 1.5,
};

const AGENT_STATUS_COPY: Record<string, { label: string; description: string; color: string }> = {
  idle: { label: 'Online', description: 'Ready to assist with Revit modeling & TNCDBR compliance.', color: 'cyan.400' },
  listening: { label: 'Listening', description: 'Go ahead -- ask REVVY anything.', color: 'cyan.300' },
  thinking: { label: 'Thinking', description: 'Working on it...', color: 'purple.300' },
  speaking: { label: 'Speaking', description: 'REVVY is replying.', color: 'teal.300' },
};

const FOOTER_TAGS = [
  { key: 'voice', label: 'Voice Input', Icon: MicIcon },
  { key: 'citations', label: 'Cited Answers', Icon: BookIcon },
  { key: 'model-aware', label: 'Model-Aware', Icon: CubeIcon },
  { key: 'always-on', label: '24/7 Available', Icon: ClockIcon },
];

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffMin = Math.round(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} min${diffMin === 1 ? '' : 's'} ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hr${diffHr === 1 ? '' : 's'} ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`;
}

/** Signed-in home dashboard -- fixed to one screen (no page scroll), every panel wired to a real REVVY module or real data. */
export function DashboardHome() {
  const { user, logout } = useAuth();
  const voiceAgent = useVoiceAgentBridge();
  const navigate = useNavigate();
  const { data: sessions } = useChatSessions();
  const createSession = useCreateChatSession();
  const [menuOpen, setMenuOpen] = useState(false);

  const visibleModules = useMemo(
    () => MODULES.filter((m) => !m.adminOnly || user?.is_admin),
    [user?.is_admin],
  );

  const recentSessions = useMemo(
    () =>
      [...(sessions ?? [])]
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        .slice(0, 3),
    [sessions],
  );

  const voiceError = voiceAgent.isEmbedded ? voiceAgent.systemStatus.error : null;
  const statusCopy = voiceError
    ? { label: 'Attention needed', description: voiceError, color: 'orange.400' }
    : AGENT_STATUS_COPY[voiceAgent.isEmbedded ? voiceAgent.agentState : 'idle'];

  const handleLogout = () => {
    void logout().then(() => navigate('/login'));
  };

  const handleNewChat = async () => {
    const session = await createSession.mutateAsync({});
    navigate(`/chat/${session.id}`);
  };

  const quickActions: QuickAction[] = [
    { key: 'new-chat', label: 'New Chat', Icon: PlusIcon, onClick: () => void handleNewChat() },
    { key: 'code-check', label: 'Code Check', Icon: ShieldCheckIcon, to: '/code-search' },
    { key: 'model-query', label: 'Model Query', Icon: CubeIcon, to: '/model-query' },
    { key: 'reports', label: 'View Reports', Icon: ChartIcon, to: '/analytics' },
    ...(user?.is_admin
      ? [
          { key: 'library', label: 'Code Library', Icon: BookIcon, to: '/code-library' },
          { key: 'admin', label: 'Admin Panel', Icon: UsersIcon, to: '/admin' },
        ]
      : []),
  ];

  return (
    <Box h="100dvh" overflow="hidden" bg="gray.950" color="whiteAlpha.900" display="flex" flexDirection="column" px={{ base: 2, md: 5 }} py={{ base: 2, md: 4 }}>
      <Box
        position="relative"
        flex="1"
        minH={0}
        maxW="1700px"
        w="full"
        mx="auto"
        display="flex"
        flexDirection="column"
        border="1px solid"
        borderColor="whiteAlpha.150"
        borderRadius="3xl"
        bg="linear-gradient(180deg, rgba(11,18,32,0.9), rgba(6,10,20,0.9))"
        boxShadow="0 0 60px rgba(56,224,255,0.06)"
        overflow="hidden"
      >
        {/* Header */}
        <HStack
          as="header"
          flexShrink={0}
          w="full"
          px={{ base: 3, lg: 7 }}
          py={3}
          justify="space-between"
          borderBottom="1px solid"
          borderColor="whiteAlpha.100"
        >
          <Box asChild _hover={{ opacity: 0.85 }} transition="opacity 0.15s ease">
            <RouterLink to="/">
              <HStack gap={3} cursor="pointer">
                <Text fontWeight="bold" letterSpacing="widest" color="whiteAlpha.900">
                  REVVY
                </Text>
                <Box w="1px" h="16px" bg="whiteAlpha.200" />
                <Text fontSize="xs" color="cyan.400" letterSpacing="wider" display={{ base: 'none', sm: 'block' }}>
                  REVIT ASSISTANT
                </Text>
              </HStack>
            </RouterLink>
          </Box>

          <HStack gap={3}>
            <HStack
              gap={2}
              px={3}
              py={1.5}
              borderRadius="full"
              border="1px solid"
              borderColor="whiteAlpha.150"
              display={{ base: 'none', md: 'flex' }}
            >
              <Text fontSize="xs" color="whiteAlpha.700">
                {user?.email}
              </Text>
            </HStack>
            {user?.is_admin && (
              <Box
                px={3}
                py={1.5}
                borderRadius="full"
                border="1px solid"
                borderColor="cyan.700"
                fontSize="xs"
                color="cyan.300"
                display={{ base: 'none', md: 'block' }}
              >
                ADMIN
              </Box>
            )}
            <HStack gap={2} px={3} py={1.5} borderRadius="full" border="1px solid" borderColor="whiteAlpha.150">
              <Box w="8px" h="8px" borderRadius="full" bg="green.400" boxShadow="0 0 6px 1px rgba(72,255,146,0.7)" />
              <Text fontSize="xs" color="green.300">
                ONLINE
              </Text>
            </HStack>

            <Box position="relative">
              <MotionButton
                type="button"
                aria-label="Menu"
                onClick={() => setMenuOpen((v) => !v)}
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.94 }}
                display="flex"
                alignItems="center"
                justifyContent="center"
                w="34px"
                h="34px"
                borderRadius="full"
                border="1px solid"
                borderColor="whiteAlpha.150"
                bg="transparent"
                color="whiteAlpha.800"
              >
                <MenuIcon size={16} />
              </MotionButton>
              {menuOpen && (
                <MotionBox
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  position="absolute"
                  top="42px"
                  right={0}
                  w="220px"
                  bg="gray.900"
                  border="1px solid"
                  borderColor="whiteAlpha.150"
                  borderRadius="xl"
                  boxShadow="xl"
                  py={2}
                  zIndex={20}
                >
                  {visibleModules.map((m) => (
                    <Box
                      key={m.key}
                      asChild
                      display="block"
                      px={4}
                      py={2}
                      fontSize="sm"
                      color="whiteAlpha.800"
                      _hover={{ bg: 'whiteAlpha.100', color: 'cyan.300' }}
                      onClick={() => setMenuOpen(false)}
                    >
                      <RouterLink to={m.to}>{m.label}</RouterLink>
                    </Box>
                  ))}
                  <Box
                    asChild
                    display="block"
                    px={4}
                    py={2}
                    fontSize="sm"
                    color="whiteAlpha.800"
                    _hover={{ bg: 'whiteAlpha.100', color: 'cyan.300' }}
                    onClick={() => setMenuOpen(false)}
                  >
                    <RouterLink to="/profile">Profile</RouterLink>
                  </Box>
                  <Box mt={1} pt={2} borderTop="1px solid" borderColor="whiteAlpha.100">
                    <MotionButton
                      type="button"
                      whileHover={{ backgroundColor: 'rgba(255,255,255,0.1)' }}
                      display="block"
                      w="full"
                      textAlign="left"
                      px={4}
                      py={2}
                      fontSize="sm"
                      color="red.300"
                      bg="transparent"
                      border="none"
                      onClick={() => {
                        setMenuOpen(false);
                        handleLogout();
                      }}
                    >
                      Log out
                    </MotionButton>
                  </Box>
                </MotionBox>
              )}
            </Box>
          </HStack>
        </HStack>

        {/* Body */}
        <Grid
          flex="1"
          minH={0}
          templateColumns={{ base: '1fr', lg: '260px 1fr 280px' }}
          gap={4}
          px={{ base: 3, lg: 6 }}
          py={4}
          overflow="hidden"
        >
          <GridItem minW={0} h="full" minH={0} display="flex" flexDirection="column" overflow="hidden">
            <VStack
              flexShrink={0}
              align="stretch"
              gap={1.5}
              bg="whiteAlpha.50"
              border="1px solid"
              borderColor="whiteAlpha.100"
              borderRadius="xl"
              p={3.5}
            >
              <Text fontSize="10px" letterSpacing="wider" color="whiteAlpha.600" textTransform="uppercase">
                REVVY Status
              </Text>
              <HStack gap={3}>
                <Box position="relative" w="36px" h="36px" flexShrink={0}>
                  <MotionBox
                    position="absolute"
                    inset={0}
                    borderRadius="full"
                    border="2px solid"
                    borderColor={statusCopy.color}
                    animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
                    transition={{ duration: voiceAgent.agentState === 'thinking' ? 0.9 : 2.5, repeat: Infinity, ease: 'easeInOut' }}
                  />
                  <Box position="absolute" inset="8px" borderRadius="full" bg={statusCopy.color} boxShadow="0 0 12px 2px rgba(56,224,255,0.6)" />
                </Box>
                <Box minW={0}>
                  <HStack gap={1.5}>
                    <Text fontWeight="semibold" fontSize="sm" color={statusCopy.color}>
                      {statusCopy.label}
                    </Text>
                    {voiceAgent.isEmbedded && (
                      <Text fontSize="9px" color="whiteAlpha.400" letterSpacing="wide">
                        🎙 VOICE AGENT
                      </Text>
                    )}
                  </HStack>
                  <Text fontSize="xs" color="whiteAlpha.600" lineClamp={2}>
                    {statusCopy.description}
                  </Text>
                </Box>
              </HStack>

              {voiceAgent.isEmbedded && (
                <HStack
                  gap={0}
                  bg="whiteAlpha.100"
                  borderRadius="lg"
                  p="2px"
                  mt={1}
                  alignSelf="flex-start"
                >
                  {(['voice', 'text'] as const).map((mode) => {
                    const active = (voiceAgent.systemStatus.mode ?? 'voice') === mode;
                    const Icon = mode === 'voice' ? MicIcon : ChatIcon;
                    return (
                      <MotionButton
                        key={mode}
                        type="button"
                        onClick={() => voiceAgent.setMode(mode)}
                        display="flex"
                        alignItems="center"
                        gap={1.5}
                        px={2.5}
                        py={1}
                        borderRadius="md"
                        bg={active ? 'whiteAlpha.200' : 'transparent'}
                        color={active ? 'white' : 'whiteAlpha.500'}
                        fontSize="xs"
                        fontWeight="medium"
                        textTransform="capitalize"
                        whileTap={{ scale: 0.95 }}
                      >
                        <Icon size={13} />
                        {mode}
                      </MotionButton>
                    );
                  })}
                </HStack>
              )}
            </VStack>

            <VStack
              align="stretch"
              gap={0.5}
              bg="whiteAlpha.50"
              border="1px solid"
              borderColor="whiteAlpha.100"
              borderRadius="xl"
              p={3}
              mt={3}
              flex="1"
              minH={0}
              overflowY="auto" className="revvy-scroll"
            >
              <Text fontSize="10px" letterSpacing="wider" color="whiteAlpha.600" textTransform="uppercase" mb={1}>
                Assistant Modules
              </Text>
              {visibleModules.map((m) => (
                <Box
                  key={m.key}
                  asChild
                  display="block"
                  borderRadius="lg"
                  px={1.5}
                  py={1.5}
                  cursor="pointer"
                  transition="all 0.15s ease"
                  _hover={{ bg: 'whiteAlpha.100', transform: 'translateX(4px)' }}
                >
                  <RouterLink to={m.to}>
                    <HStack gap={2.5} align="center">
                      <Box
                        w="28px"
                        h="28px"
                        flexShrink={0}
                        borderRadius="lg"
                        border="1px solid"
                        borderColor="whiteAlpha.150"
                        bg="whiteAlpha.50"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="cyan.300"
                      >
                        <m.Icon size={14} />
                      </Box>
                      <Box flex={1} minW={0}>
                        <Text fontSize="xs" fontWeight="medium">
                          {m.label}
                        </Text>
                        <Text fontSize="10px" color="whiteAlpha.500" lineClamp={1}>
                          {m.description}
                        </Text>
                      </Box>
                      <Box color="whiteAlpha.400">
                        <ChevronRightIcon size={14} />
                      </Box>
                    </HStack>
                  </RouterLink>
                </Box>
              ))}
            </VStack>
          </GridItem>

          <GridItem minW={0} h="full" minH={0} overflow="hidden">
            <VStack h="full" minH={0} gap={3} align="center" justify="center">
              <VStack gap={0} textAlign="center" flexShrink={0}>
                <Heading size={{ base: 'lg', xl: 'xl' }} letterSpacing="widest">
                  REVVY
                </Heading>
                <Text fontSize="10px" letterSpacing="widest" color="cyan.300" textTransform="uppercase">
                  Your AI Revit Copilot
                </Text>
              </VStack>

              <Box flex="1" minH={0} w="full" display={{ base: 'flex', md: 'none' }} justifyContent="center" alignItems="center">
                <OrbVisual size="min(220px, 30vh)" state={voiceAgent.agentState} />
              </Box>
              <Box flex="1" minH={0} w="full" display={{ base: 'none', md: 'flex' }} justifyContent="center" alignItems="center">
                <ModuleOrbit items={visibleModules} orbState={voiceAgent.agentState} />
              </Box>

              <Box flexShrink={0} w="full">
                <AskBar modules={visibleModules} isEmbedded={voiceAgent.isEmbedded} />
              </Box>
            </VStack>
          </GridItem>

          <GridItem minW={0} h="full" minH={0} display="flex" flexDirection="column" overflow="hidden">
            <VStack
              flexShrink={0}
              align="stretch"
              gap={1.5}
              bg="whiteAlpha.50"
              border="1px solid"
              borderColor="whiteAlpha.100"
              borderRadius="xl"
              p={3}
            >
              <Text fontSize="10px" letterSpacing="wider" color="whiteAlpha.600" textTransform="uppercase" mb={0.5}>
                Quick Tools
              </Text>
              <Grid templateColumns="repeat(2, 1fr)" gap={2}>
                {quickActions.map((qa) =>
                  'to' in qa ? (
                    <Box key={qa.key} asChild transition="all 0.15s ease" _hover={{ borderColor: 'cyan.400', transform: 'translateY(-3px)' }} {...tileStyle}>
                      <RouterLink to={qa.to}>
                        <Box color="cyan.300">
                          <qa.Icon size={18} />
                        </Box>
                        <Text fontSize="10px" fontWeight="medium" color="whiteAlpha.800" textAlign="center">
                          {qa.label}
                        </Text>
                      </RouterLink>
                    </Box>
                  ) : (
                    <MotionButton
                      key={qa.key}
                      type="button"
                      onClick={qa.onClick}
                      disabled={createSession.isPending}
                      whileHover={{ y: -3, borderColor: '#22d3ee' }}
                      whileTap={{ scale: 0.97 }}
                      {...tileStyle}
                    >
                      <Box color="cyan.300">
                        <qa.Icon size={18} />
                      </Box>
                      <Text fontSize="10px" fontWeight="medium" color="whiteAlpha.800" textAlign="center">
                        {qa.label}
                      </Text>
                    </MotionButton>
                  ),
                )}
              </Grid>
            </VStack>

            <VStack
              align="stretch"
              gap={1}
              bg="whiteAlpha.50"
              border="1px solid"
              borderColor="whiteAlpha.100"
              borderRadius="xl"
              p={3}
              mt={3}
              flex="1"
              minH={0}
              overflowY="auto" className="revvy-scroll"
            >
              <Text fontSize="10px" letterSpacing="wider" color="whiteAlpha.600" textTransform="uppercase" mb={0.5}>
                Recent Activity
              </Text>
              {recentSessions.length === 0 ? (
                <Text fontSize="xs" color="whiteAlpha.500">
                  No activity yet -- start a chat to see it here.
                </Text>
              ) : (
                <>
                  <AnimatedList
                    items={recentSessions}
                    getKey={(s) => s.id}
                    renderItem={(s) => (
                      <Box
                        asChild
                        display="block"
                        borderRadius="lg"
                        px={1.5}
                        py={1.5}
                        cursor="pointer"
                        transition="all 0.15s ease"
                        _hover={{ bg: 'whiteAlpha.100', transform: 'translateX(4px)' }}
                      >
                        <RouterLink to={`/chat/${s.id}`}>
                          <HStack justify="space-between" gap={3}>
                            <Text fontSize="xs" color="whiteAlpha.800" truncate>
                              {s.title ?? 'Untitled chat'}
                            </Text>
                            <Text fontSize="10px" color="whiteAlpha.500" whiteSpace="nowrap">
                              {formatRelativeTime(s.updated_at)}
                            </Text>
                          </HStack>
                        </RouterLink>
                      </Box>
                    )}
                  />
                  <Box asChild fontSize="10px" color="cyan.400" mt={0.5} _hover={{ color: 'cyan.300' }}>
                    <RouterLink to="/chat">View all chats &rarr;</RouterLink>
                  </Box>
                </>
              )}
            </VStack>
          </GridItem>
        </Grid>

        {/* Footer strip -- real value props only */}
        <HStack
          flexShrink={0}
          justify="center"
          gap={{ base: 4, md: 10 }}
          py={2.5}
          borderTop="1px solid"
          borderColor="whiteAlpha.100"
          flexWrap="wrap"
        >
          {FOOTER_TAGS.map((tag) => (
            <HStack key={tag.key} gap={1.5} color="whiteAlpha.500">
              <Box color="cyan.500">
                <tag.Icon size={13} />
              </Box>
              <Text fontSize="10px" letterSpacing="wide" textTransform="uppercase">
                {tag.label}
              </Text>
            </HStack>
          ))}
        </HStack>
      </Box>
    </Box>
  );
}
