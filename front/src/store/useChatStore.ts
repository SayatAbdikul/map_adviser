import { create } from 'zustand';

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: number;
}

interface ChatState {
  isOpen: boolean;
  messages: Message[];
  isTyping: boolean;
  toggleChat: () => void;
  setIsOpen: (isOpen: boolean) => void;
  addMessage: (message: Message) => void;
  setTyping: (isTyping: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isOpen: false,
  messages: [],
  isTyping: false,
  toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),
  setIsOpen: (isOpen) => set({ isOpen }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setTyping: (isTyping) => set({ isTyping }),
}));
