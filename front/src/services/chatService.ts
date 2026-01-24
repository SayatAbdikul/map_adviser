import type { Message } from '@/store/useChatStore';

export const chatService = {
  sendMessage: async (text: string): Promise<Message> => {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 1000));
    
    return {
      id: Date.now().toString(),
      text: `I received: "${text}". How can I help you with the map?`,
      sender: 'bot',
      timestamp: Date.now(),
    };
  },
};
