import React, { useState, useRef, useEffect } from 'react';
import { Send, MapPin, Clock, Users, Bot, User, Loader2, X } from 'lucide-react';
import { useRoomStore } from '@/store/useRoomStore';
import type { ChatMessage, ChatRouteData } from '@/types';

interface RoomChatProps {
  isOpen: boolean;
  onClose: () => void;
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
};

const formatDuration = (minutes: number) => {
  if (minutes < 1) return '< 1 мин';
  if (minutes < 60) return `${Math.round(minutes)} мин`;
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return `${hours}ч ${mins}мин`;
};

const ChatMessageItem: React.FC<{ message: ChatMessage; isOwn: boolean }> = ({ message, isOwn }) => {
  const routeData = message.route_data;
  
  return (
    <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} mb-3`}>
      {/* Sender name */}
      <span className={`text-xs ${message.is_agent_response ? 'text-purple-600' : 'text-gray-500'} mb-1 flex items-center gap-1`}>
        {message.is_agent_response ? (
          <Bot size={12} />
        ) : (
          <User size={12} />
        )}
        {message.sender_nickname}
      </span>
      
      {/* Message bubble */}
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 ${
          message.is_agent_response
            ? 'bg-purple-50 border border-purple-100'
            : isOwn
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        
        {/* Route data visualization */}
        {routeData && <RouteDataCard routeData={routeData} />}
      </div>
      
      {/* Timestamp */}
      <span className="text-xs text-gray-400 mt-1">
        {formatTime(message.timestamp)}
      </span>
    </div>
  );
};

const RouteDataCard: React.FC<{ routeData: ChatRouteData }> = ({ routeData }) => {
  if (routeData.type === 'meeting_place') {
    return (
      <div className="mt-2 p-2 bg-white rounded border border-purple-200">
        <div className="flex items-center gap-1 text-purple-700 font-medium text-sm mb-2">
          <MapPin size={14} />
          {routeData.destination.name}
        </div>
        <p className="text-xs text-gray-500 mb-2">{routeData.destination.address}</p>
        
        {routeData.member_travel_times && routeData.member_travel_times.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs text-gray-600 font-medium flex items-center gap-1">
              <Clock size={12} />
              Время в пути:
            </div>
            {routeData.member_travel_times.map((tt) => (
              <div key={tt.member_id} className="flex justify-between text-xs">
                <span className="text-gray-600">{tt.member_nickname}:</span>
                <span className="text-gray-800 font-medium">
                  {tt.error ? 'Ошибка' : formatDuration(tt.duration_minutes)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  if (routeData.type === 'routes_to_destination') {
    return (
      <div className="mt-2 p-2 bg-white rounded border border-purple-200">
        <div className="flex items-center gap-1 text-purple-700 font-medium text-sm mb-2">
          <MapPin size={14} />
          {routeData.destination.name}
        </div>
        
        {routeData.member_routes && routeData.member_routes.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs text-gray-600 font-medium flex items-center gap-1">
              <Users size={12} />
              Маршруты участников:
            </div>
            {routeData.member_routes.map((route) => (
              <div key={route.member_id} className="flex justify-between text-xs">
                <span className="text-gray-600">{route.member_nickname}:</span>
                <span className="text-gray-800 font-medium">
                  {formatDuration(route.duration_minutes)} • {(route.distance_meters / 1000).toFixed(1)} км
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  
  return null;
};

export const RoomChat: React.FC<RoomChatProps> = ({ isOpen, onClose }) => {
  const {
    chatMessages,
    isAgentTyping,
    myId,
    members,
    sendChatMessage,
  } = useRoomStore();
  
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAgentTyping]);
  
  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);
  
  const handleSend = () => {
    if (input.trim()) {
      sendChatMessage(input.trim());
      setInput('');
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const membersWithLocation = Array.from(members.values()).filter(m => m.location).length;
  
  if (!isOpen) return null;
  
  return (
    <div className="absolute top-4 left-4 z-30 w-80 h-[500px] bg-white rounded-lg shadow-xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gradient-to-r from-purple-500 to-blue-500">
        <div className="flex items-center gap-2 text-white">
          <Bot size={20} />
          <span className="font-medium">Чат комнаты</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-white/80 hover:text-white rounded"
        >
          <X size={18} />
        </button>
      </div>
      
      {/* Info bar */}
      <div className="px-4 py-2 bg-gray-50 border-b text-xs text-gray-500 flex items-center gap-4">
        <span className="flex items-center gap-1">
          <Users size={12} />
          {membersWithLocation} с местоположением
        </span>
        <span className="text-gray-300">•</span>
        <span>Спроси: "Найди кафе для всех"</span>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {chatMessages.length === 0 && (
          <div className="text-center text-gray-400 text-sm py-8">
            <Bot size={32} className="mx-auto mb-2 text-gray-300" />
            <p>Напишите сообщение, чтобы найти</p>
            <p>место встречи для всех участников</p>
          </div>
        )}
        
        {chatMessages.map((message) => (
          <ChatMessageItem
            key={message.id}
            message={message}
            isOwn={message.sender_id === myId}
          />
        ))}
        
        {/* Typing indicator */}
        {isAgentTyping && (
          <div className="flex items-center gap-2 text-purple-600 text-sm">
            <Loader2 size={14} className="animate-spin" />
            <span>Помощник думает...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <div className="p-3 border-t">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Найди ближайшее кафе..."
            disabled={isAgentTyping}
            className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:bg-gray-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isAgentTyping}
            className="px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};
