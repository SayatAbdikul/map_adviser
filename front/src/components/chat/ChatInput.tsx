import React, { useState } from 'react';
import { Send, Car, PersonStanding, Bus } from 'lucide-react';
import { useChatStore } from '@/store/useChatStore';
import { useRouteStore } from '@/store/useRouteStore';
import { chatService } from '@/services/chatService';
import { Button } from '@/components/common/Button';

type TransportMode = 'driving' | 'walking' | 'public_transport';

const TRANSPORT_MODES: { mode: TransportMode; icon: React.ReactNode; label: string }[] = [
  { mode: 'driving', icon: <Car size={16} />, label: 'Машина' },
  { mode: 'walking', icon: <PersonStanding size={16} />, label: 'Пешком' },
  { mode: 'public_transport', icon: <Bus size={16} />, label: 'Транспорт' },
];

export const ChatInput: React.FC = () => {
  const [text, setText] = useState('');
  const [transportMode, setTransportMode] = useState<TransportMode>('driving');
  const { addMessage, setTyping } = useChatStore();
  const { setRouteResponse, setLoading, setError } = useRouteStore();
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!text.trim() || isSending) return;

    const userMsg = text.trim();
    const modeLabel = TRANSPORT_MODES.find(m => m.mode === transportMode)?.label || transportMode;
    setText('');
    setIsSending(true);
    setLoading(true);

    // Add user message with mode indicator
    addMessage({
      id: Date.now().toString(),
      text: `${userMsg} [${modeLabel}]`,
      sender: 'user',
      timestamp: Date.now(),
    });

    setTyping(true);

    try {
      const response = await chatService.sendMessage(userMsg, transportMode);
      
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
    <div className="p-3 app-surface border-t app-border">
      {/* Transport Mode Selector */}
      <div className="flex items-center gap-1 mb-2">
        {TRANSPORT_MODES.map(({ mode, icon, label }) => (
          <button
            key={mode}
            type="button"
            onClick={() => setTransportMode(mode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              transportMode === mode
                ? 'bg-[color:var(--app-accent)] text-[color:var(--app-accent-contrast)]'
                : 'bg-[color:var(--app-surface-2)] text-[color:var(--app-muted)] hover:bg-[color:var(--app-surface-3)]'
            }`}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form
        onSubmit={handleSend}
        className="flex items-center gap-2"
      >
        <input
          type="text"
          className="flex-1 bg-[color:var(--app-surface-2)] text-[color:var(--app-text)] placeholder-[color:var(--app-muted)] border-0 rounded-full px-4 py-2 focus:ring-2 focus:ring-[color:var(--app-ring)] focus:bg-[color:var(--app-surface)] transition-colors"
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
    </div>
  );
};
