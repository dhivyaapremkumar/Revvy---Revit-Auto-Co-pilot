import { Box, Text } from '@chakra-ui/react';
import type { ChatMessage } from '../../types';

export interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <Box
      alignSelf={isUser ? 'flex-end' : 'flex-start'}
      maxW="75%"
      px={4}
      py={3}
      borderRadius="2xl"
      bg={isUser ? 'brand.500' : 'whiteAlpha.800'}
      color={isUser ? 'white' : 'gray.800'}
      boxShadow="sm"
      _dark={{ bg: isUser ? 'brand.500' : 'blackAlpha.400', color: isUser ? 'white' : 'gray.100' }}
    >
      <Text whiteSpace="pre-wrap" fontSize="sm">
        {message.content}
      </Text>
    </Box>
  );
}
