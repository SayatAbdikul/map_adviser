import React from 'react';
import { twMerge } from 'tailwind-merge';
import { useChatStore } from '@/store/useChatStore';
import { Minus } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export const ChatDrawer: React.FC = () => {
  const { isOpen, toggleChat } = useChatStore();
  
  return (
    <div
      className={twMerge(
        'fixed bottom-0 right-0 z-40 w-full sm:w-96 bg-white shadow-2xl transition-transform duration-300 ease-in-out transform rounded-t-xl sm:rounded-tl-xl sm:rounded-bl-none sm:right-4',
        isOpen ? 'translate-y-0' : 'translate-y-full'
      )}
      style={{ height: '500px', maxHeight: '80vh' }}
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div 
            className="flex items-center justify-between p-3 border-b border-gray-100 bg-blue-600 text-white rounded-t-xl cursor-pointer"
            onClick={toggleChat}
        >
          <div className="flex items-center space-x-2">
            <span className="font-semibold">Map Assistant</span>
          </div>
          <div className="flex items-center space-x-1">
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); toggleChat(); }} className="text-white hover:bg-blue-700 h-8 w-8 p-0">
               <Minus size={20} />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden relative flex flex-col bg-gray-50">
           <MessageList />
           <ChatInput />
        </div>
      </div>
    </div>
  );
};
