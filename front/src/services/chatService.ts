import type { Message } from '@/store/useChatStore';
import type { RouteResponse, RouteRequest, Route } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Format duration in minutes to human-readable string
 */
const formatDuration = (minutes: number | null | undefined): string => {
  if (minutes === null || minutes === undefined) return 'неизвестно';
  if (minutes < 1) return 'меньше минуты';
  if (minutes < 60) return `${Math.round(minutes)} мин`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = Math.round(minutes % 60);
  if (remainingMinutes === 0) return `${hours} ч`;
  return `${hours} ч ${remainingMinutes} мин`;
};

/**
 * Format distance in meters to human-readable string
 */
const formatDistance = (meters: number | null | undefined): string => {
  if (meters === null || meters === undefined) return 'неизвестно';
  if (meters < 1000) return `${Math.round(meters)} м`;
  return `${(meters / 1000).toFixed(1)} км`;
};

/**
 * Get transport mode display name
 */
const getTransportModeDisplay = (mode: string | undefined): string => {
  switch (mode) {
    case 'driving': return '🚗 На машине';
    case 'walking': return '🚶 Пешком';
    case 'public_transport': return '🚌 На общественном транспорте';
    default: return mode || 'неизвестно';
  }
};

/**
 * Format route response into a readable chat message
 */
const formatRouteMessage = (response: RouteResponse): string => {
  const { request_summary, routes } = response;
  
  if (!routes || routes.length === 0) {
    return 'К сожалению, не удалось построить маршрут. Попробуйте уточнить запрос.';
  }

  const route = routes[0] as Route;
  const lines: string[] = [];

  // Header with intent
  lines.push(`🗺️ ${request_summary.intent}`);
  lines.push('');

  // Route summary
  lines.push(`📍 Маршрут: ${route.title}`);
  lines.push(`📏 Расстояние: ${formatDistance(route.total_distance_meters)}`);
  lines.push(`⏱️ Время в пути: ${formatDuration(route.total_duration_minutes)}`);
  lines.push(getTransportModeDisplay(request_summary.transport_mode));
  
  // Public transport specific info
  if (route.transport_chain) {
    lines.push(`🚇 Маршрут: ${route.transport_chain}`);
    if (route.transfer_count !== undefined) {
      lines.push(`🔄 Пересадок: ${route.transfer_count}`);
    }
    if (route.walking_duration_minutes !== undefined) {
      lines.push(`🚶 Ходьба: ${formatDuration(route.walking_duration_minutes)}`);
    }
  }
  lines.push('');

  // Waypoints
  if (route.waypoints && route.waypoints.length > 0) {
    lines.push('Маршрут проходит через:');
    route.waypoints.forEach((wp, index) => {
      const icon = wp.type === 'start' ? '🟢' : wp.type === 'end' ? '🔴' : '📍';
      lines.push(`${icon} ${index + 1}. ${wp.name} (${wp.address})`);
    });
    lines.push('');
  }

  // Turn-by-turn directions (show first few)
  if (route.directions && route.directions.length > 0) {
    lines.push('Основные повороты:');
    const mainDirections = route.directions
      .filter(d => d.instruction && d.type !== 'begin' && d.type !== 'end')
      .slice(0, 5);
    
    mainDirections.forEach((dir) => {
      if (dir.instruction) {
        lines.push(`➡️ ${dir.instruction}`);
      }
    });
    
    if (route.directions.length > 5) {
      lines.push(`... и ещё ${route.directions.length - 5} поворотов`);
    }
  }

  // If multiple routes available
  if (routes.length > 1) {
    lines.push('');
    lines.push(`📊 Также доступно ещё ${routes.length - 1} вариантов маршрута.`);
  }

  return lines.join('\n');
};

/**
 * Format error into a user-friendly message
 */
const formatErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      return '❌ Не удалось подключиться к серверу. Проверьте, запущен ли бэкенд на порту 8000.';
    }
    return `❌ Ошибка: ${error.message}`;
  }
  return '❌ Произошла неизвестная ошибка. Попробуйте ещё раз.';
};

export interface ChatServiceResponse {
  message: Message;
  routeData: RouteResponse | null;
}

export const chatService = {
  /**
   * Send a route query to the backend
   */
  sendMessage: async (text: string, mode: 'driving' | 'walking' | 'public_transport' = 'driving'): Promise<ChatServiceResponse> => {
    const requestBody: RouteRequest = {
      query: text,
      mode: mode,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      console.log('response', response);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : errorData.detail?.error || 'Request failed';
        throw new Error(errorMessage);
      }

      const routeResponse: RouteResponse = await response.json();
      
      return {
        message: {
          id: Date.now().toString(),
          text: formatRouteMessage(routeResponse),
          sender: 'bot',
          timestamp: Date.now(),
        },
        routeData: routeResponse,
      };
    } catch (error) {
      console.error('Chat service error:', error);
      return {
        message: {
          id: Date.now().toString(),
          text: formatErrorMessage(error),
          sender: 'bot',
          timestamp: Date.now(),
        },
        routeData: null,
      };
    }
  },

  /**
   * Format route for display (utility function)
   */
  formatRoute: formatRouteMessage,
  formatDuration,
  formatDistance,
};
