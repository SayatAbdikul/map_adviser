import React, { useEffect, useRef, useState } from 'react';
import { twMerge } from 'tailwind-merge';
import { useChatStore } from '@/store/useChatStore';
import { ChevronUp, Minus, MessageSquare } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { AgentReasoningPanel } from './AgentReasoningPanel';

export const ChatDrawer: React.FC = () => {
  const { isOpen, setIsOpen, toggleChat } = useChatStore();
  const [sheetSize, setSheetSize] = useState<'collapsed' | 'half' | 'full'>(
    'collapsed'
  );
  const touchStartY = useRef<number | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setSheetSize('collapsed');
      return;
    }

    if (sheetSize === 'collapsed') {
      setSheetSize('half');
    }
  }, [isOpen, sheetSize]);

  const handleTouchStart = (event: React.TouchEvent) => {
    touchStartY.current = event.touches[0]?.clientY ?? null;
  };

  const handleTouchEnd = (event: React.TouchEvent) => {
    if (touchStartY.current === null) return;
    const endY = event.changedTouches[0]?.clientY ?? touchStartY.current;
    const delta = endY - touchStartY.current;

    if (delta < -60) {
      setIsOpen(true);
      setSheetSize(sheetSize === 'half' ? 'full' : 'half');
    } else if (delta > 60) {
      if (sheetSize === 'full') {
        setSheetSize('half');
      } else {
        setIsOpen(false);
      }
    }

    touchStartY.current = null;
  };

  const sheetHeight =
    sheetSize === 'collapsed' ? '72px' : sheetSize === 'half' ? '50vh' : '92vh';

  return (
    <div
      className={twMerge(
        'fixed bottom-0 left-0 z-40 w-full app-surface app-shadow transition-all duration-300 ease-in-out rounded-t-2xl border-t app-border'
      )}
      style={{ height: sheetHeight }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="flex flex-col h-full">
        <div
          className="flex items-center justify-center py-2 cursor-pointer"
          onClick={() => setIsOpen(!isOpen)}
        >
          <div className="h-1.5 w-14 rounded-full bg-[color:var(--app-border)]" />
        </div>

        {isOpen ? (
          <>
            <div
              className="flex items-center justify-between px-4 py-3 border-b app-border app-accent rounded-t-2xl"
              onClick={toggleChat}
            >
              <div className="flex items-center space-x-2">
                <MessageSquare size={18} />
                <span className="font-semibold">Map Assistant</span>
              </div>
              <div className="flex items-center space-x-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={e => {
                    e.stopPropagation();
                    if (sheetSize === 'full') {
                      setSheetSize('half');
                      return;
                    }
                    toggleChat();
                  }}
                  className="text-[color:var(--app-accent-contrast)] hover:bg-[color:var(--app-accent-strong)] h-8 w-8 p-0"
                >
                  <Minus size={20} />
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden min-h-0 relative flex flex-col app-surface-2">
              <AgentReasoningPanel />
              <div className="flex-1 overflow-hidden min-h-0">
                <MessageList />
              </div>
              <ChatInput />
            </div>
          </>
        ) : (
          <div className="px-4 pb-4">
            <button
              type="button"
              onClick={() => setIsOpen(true)}
              className="w-full flex items-center justify-between gap-3 rounded-2xl border app-border px-4 py-3 text-left app-muted app-shadow-soft"
            >
              <span className="text-sm">Ask about a route or place...</span>
              <ChevronUp size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
