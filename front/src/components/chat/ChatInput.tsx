import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { useChatStore } from '@/store/useChatStore';
import { chatService } from '@/services/chatService';
import { Button } from '@/components/common/Button';

export const ChatInput: React.FC = () => {
  const [text, setText] = useState('');
  const { addMessage, setTyping } = useChatStore();
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!text.trim() || isSending) return;

    const userMsg = text.trim();
    setText('');
    setIsSending(true);

    // Add user message
    addMessage({
      id: Date.now().toString(),
      text: userMsg,
      sender: 'user',
      timestamp: Date.now(),
    });

    setTyping(true);

    try {
      const response = await chatService.sendMessage(userMsg);
      addMessage(response);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setTyping(false);
      setIsSending(false);
    }
  };

  return (
    <form 
      onSubmit={handleSend}
      className="p-3 bg-white border-t border-gray-100 flex items-center gap-2"
    >
      <input
        type="text"
        className="flex-1 bg-gray-100 text-gray-900 placeholder-gray-500 border-0 rounded-full px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"
        placeholder="Type a message..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button 
        type="submit" 
        variant="primary" 
        size="sm"
        disabled={!text.trim() || isSending}
        className="rounded-full w-10 h-10 p-0 flex-shrink-0"
      >
        <Send size={18} className={text.trim() ? "ml-1" : ""} />
      </Button>
    </form>
  );
};
