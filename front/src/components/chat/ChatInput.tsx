import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Send, Car, PersonStanding, Bus, Mic, MicOff } from 'lucide-react';
import { useChatStore } from '@/store/useChatStore';
import { useRouteStore } from '@/store/useRouteStore';
import { chatService } from '@/services/chatService';
import { Button } from '@/components/common/Button';

type TransportMode = 'driving' | 'walking' | 'public_transport';

const TRANSPORT_MODES: {
  mode: TransportMode;
  icon: React.ReactNode;
  label: string;
}[] = [
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
  const [isRecording, setIsRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const lastSpeechNoticeRef = useRef<{ message: string; at: number } | null>(
    null
  );

  const pushSpeechNotice = useCallback(
    (message: string) => {
      const now = Date.now();
      if (lastSpeechNoticeRef.current) {
        const { message: lastMessage, at } = lastSpeechNoticeRef.current;
        if (lastMessage === message && now - at < 10000) {
          return;
        }
      }

      lastSpeechNoticeRef.current = { message, at: now };
      addMessage({
        id: `speech-${now}`,
        text: message,
        sender: 'bot',
        timestamp: now,
      });
    },
    [addMessage]
  );

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsRecording(true);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognition.onerror = event => {
      console.error('Speech recognition error:', event);
      setIsRecording(false);

      const message = (() => {
        switch (event.error) {
          case 'not-allowed':
          case 'service-not-allowed':
            return '🎙️ Разрешите доступ к микрофону в настройках браузера.';
          case 'no-speech':
            return '🎙️ Не расслышал голос, попробуйте ещё раз.';
          case 'audio-capture':
            return '🎙️ Микрофон не найден. Проверьте подключение.';
          case 'network':
            return '🎙️ Ошибка сети при распознавании речи.';
          default:
            return '🎙️ Не удалось запустить распознавание речи.';
        }
      })();

      pushSpeechNotice(message);
    };

    recognition.onresult = event => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .map(result => result[0]?.transcript ?? '')
        .join(' ')
        .trim();

      if (!transcript) return;
      setText(prev => (prev ? `${prev} ${transcript}` : transcript));
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.onstart = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [pushSpeechNotice]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!text.trim() || isSending) return;

    if (isRecording) {
      recognitionRef.current?.stop();
    }

    const userMsg = text.trim();
    // Capture history BEFORE adding the new user message to avoid duplicating it
    const history = useChatStore.getState().messages.map(m => ({
      role: m.sender === 'bot' ? ('assistant' as const) : ('user' as const),
      content: m.text,
    }));
    const modeLabel =
      TRANSPORT_MODES.find(m => m.mode === transportMode)?.label ||
      transportMode;
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
      const response = await chatService.sendMessage(
        userMsg,
        transportMode,
        history
      );

      // Add bot response message
      addMessage(response.message);

      // Update route store with route data if available
      if (response.routeData) {
        setRouteResponse(response.routeData);
        setError(null);
      } else {
        setRouteResponse(null);
        if (response.message.text.startsWith('❌')) {
          setError(response.message.text);
        } else {
          setError(null);
        }
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

  const handleToggleRecording = () => {
    if (isSending) return;
    if (!speechSupported) {
      pushSpeechNotice(
        '🎙️ Распознавание речи не поддерживается в этом браузере.'
      );
      return;
    }
    const recognition = recognitionRef.current;
    if (!recognition) return;

    if (isRecording) {
      recognition.stop();
      return;
    }

    try {
      recognition.start();
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      setIsRecording(false);
      pushSpeechNotice('🎙️ Не удалось запустить распознавание речи.');
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
      <form onSubmit={handleSend} className="flex items-center gap-2">
        <input
          type="text"
          className="flex-1 bg-[color:var(--app-surface-2)] text-[color:var(--app-text)] placeholder-[color:var(--app-muted)] border-0 rounded-full px-4 py-2 focus:ring-2 focus:ring-[color:var(--app-ring)] focus:bg-[color:var(--app-surface)] transition-colors"
          placeholder="Введите маршрут, например: от Байтерека до EXPO..."
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <Button
          type="button"
          variant={isRecording ? 'danger' : 'secondary'}
          size="sm"
          disabled={isSending}
          aria-disabled={!speechSupported}
          onClick={handleToggleRecording}
          aria-pressed={isRecording}
          title={
            !speechSupported
              ? 'Распознавание речи не поддерживается'
              : isRecording
                ? 'Остановить запись'
                : 'Говорите для ввода'
          }
          className={`rounded-full w-10 h-10 p-0 flex-shrink-0 ${
            speechSupported ? '' : 'opacity-60 cursor-not-allowed'
          }`}
        >
          {speechSupported ? <Mic size={18} /> : <MicOff size={18} />}
        </Button>
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!text.trim() || isSending}
          className="rounded-full w-10 h-10 p-0 flex-shrink-0"
        >
          <Send size={18} className={text.trim() ? 'ml-1' : ''} />
        </Button>
      </form>
    </div>
  );
};
