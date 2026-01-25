import { API_BASE_URL, buildApiUrl } from '@/constants';
import type { Message } from '@/store/useChatStore';
import type { RouteResponse, LegacyRouteResponse, CoreAgentResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Type guard to check if response is the new core agent format
 */
const isCoreAgentResponse = (response: RouteResponse): response is CoreAgentResponse => {
    return (response as CoreAgentResponse).routes !== undefined;
};

/**
 * Type guard to check if response is the legacy format
 */
const isLegacyResponse = (response: RouteResponse): response is LegacyRouteResponse => {
    return (response as LegacyRouteResponse).places !== undefined;
};

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
 * Format route response into a readable chat message
 */
const formatRouteMessage = (response: RouteResponse): string => {
    // Handle the new core agent response format
    if (isCoreAgentResponse(response)) {
        const routes = response.routes || [];
        
        if (routes.length === 0) {
            return 'К сожалению, не удалось построить маршрут. Попробуйте уточнить запрос.';
        }

        const lines: string[] = [];
        const firstRoute = routes[0];
        const waypoints = firstRoute.waypoints || [];
        
        // Header
        lines.push('🗺️ Маршрут построен успешно!');
        lines.push('');

        // Route summary
        const distanceKm = firstRoute.total_distance_meters ? (firstRoute.total_distance_meters / 1000).toFixed(1) : 'неизвестно';
        const durationMin = firstRoute.total_duration_minutes || null;

        lines.push(`📏 Общее расстояние: ${distanceKm} км`);
        lines.push(`⏱️ Время в пути: ${formatDuration(durationMin)}`);
        
        if (firstRoute.transport_chain) {
            lines.push(`🚌 Транспорт: ${firstRoute.transport_chain}`);
        }
        
        if (firstRoute.transfer_count !== undefined) {
            lines.push(`🔄 Пересадок: ${firstRoute.transfer_count}`);
        }
        
        lines.push('');

        // Waypoints list
        if (waypoints.length > 0) {
            lines.push('📍 Точки маршрута:');
            waypoints.forEach((waypoint) => {
                const typeIcon = waypoint.type === 'start' ? '🟢' : waypoint.type === 'end' ? '🔴' : '📍';
                lines.push(`${typeIcon} **${waypoint.name}**`);
                if (waypoint.address) {
                    lines.push(`   📍 ${waypoint.address}`);
                }
            });
        }

        // Show route options if multiple
        if (routes.length > 1) {
            lines.push('');
            lines.push('🗺️ Доступные варианты маршрута:');
            routes.forEach((route, index) => {
                const distKm = route.total_distance_meters ? (route.total_distance_meters / 1000).toFixed(1) : '?';
                const durMin = route.total_duration_minutes || '?';
                lines.push(`${index + 1}. ${route.title || `Вариант ${index + 1}`} - ${distKm} км, ${durMin} мин`);
            });
        }

        return lines.join('\n');
    }

    // Handle the old routing service response format for backwards compatibility
    if (isLegacyResponse(response)) {
        const { places, route_url, total_distance, total_duration, gemini_explanation } = response;

        if (!places || places.length === 0) {
            return 'К сожалению, не удалось построить маршрут. Попробуйте уточнить запрос.';
        }

        const lines: string[] = [];

        // Header with Gemini explanation
        lines.push(`🗺️ ${gemini_explanation}`);
        lines.push('');

        // Route summary
        const distanceKm = total_distance ? (total_distance / 1000).toFixed(1) : 'неизвестно';
        const durationMin = total_duration ? Math.round(total_duration / 60) : null;

        lines.push(`📍 Найдено мест: ${places.length}`);
        lines.push(`📏 Общее расстояние: ${distanceKm} км`);
        lines.push(`⏱️ Время в пути: ${formatDuration(durationMin)}`);
        lines.push('');

        // Places list
        lines.push('📍 Места для посещения:');
        places.forEach((place, index) => {
            lines.push(`${index + 1}. **${place.name}**`);
            lines.push(`   📍 ${place.address}`);
        });

        lines.push('');
        lines.push(`🗺️ [Открыть маршрут в 2GIS](${route_url})`);

        return lines.join('\n');
    }

    // Fallback if format is not recognized
    return 'К сожалению, не удалось построить маршрут. Попробуйте уточнить запрос.';
};

/**
 * Format error into a user-friendly message
 */
const formatErrorMessage = (error: unknown): string => {
    if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            return `❌ Не удалось подключиться к серверу. Проверьте, запущен ли бэкенд (${API_BASE_URL}).`;
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
            mode,
        };

        try {
            const response = await fetch(buildApiUrl('/route'), {
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
