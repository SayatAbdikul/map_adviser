import React, { useEffect, useRef } from 'react';
import { useChatStore } from '@/store/useChatStore';
import { twMerge } from 'tailwind-merge';

export const MessageList: React.FC = () => {
  const { messages, isTyping } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && (
        <div className="text-center text-gray-400 mt-10 text-sm">
          <p>Ask me anything about the map!</p>
          <p>e.g. "Where can I find coffee?"</p>
        </div>
      )}
      
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={twMerge(
            'flex w-full',
            msg.sender === 'user' ? 'justify-end' : 'justify-start'
          )}
        >
          <div
            className={twMerge(
              'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
              msg.sender === 'user'
                ? 'bg-blue-600 text-white rounded-br-none'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm'
            )}
          >
            {msg.text}
          </div>
        </div>
      ))}

      {isTyping && (
        <div className="flex justify-start">
          <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
      
      <div ref={bottomRef} />
    </div>
  );
};
