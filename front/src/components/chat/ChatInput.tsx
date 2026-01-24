import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { useChatStore } from '@/store/useChatStore';
import { useRouteStore } from '@/store/useRouteStore';
import { chatService } from '@/services/chatService';
import { Button } from '@/components/common/Button';

export const ChatInput: React.FC = () => {
  const [text, setText] = useState('');
  const { addMessage, setTyping } = useChatStore();
  const { setRouteResponse, setLoading, setError } = useRouteStore();
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!text.trim() || isSending) return;

    const userMsg = text.trim();
    setText('');
    setIsSending(true);
    setLoading(true);

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
      
      // Add bot response message
      addMessage(response.message);
      
      // Update route store with route data if available
      if (response.routeData) {
        setRouteResponse(response.routeData);
      } else {
        setError('No route data received');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
      addMessage({
        id: Date.now().toString(),
        text: '❌ Произошла ошибка при отправке запроса.',
        sender: 'bot',
        timestamp: Date.now(),
      });
    } finally {
      setTyping(false);
      setIsSending(false);
      setLoading(false);
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
        placeholder="Введите маршрут, например: от Байтерека до EXPO..."
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
