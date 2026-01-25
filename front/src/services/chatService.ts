import type { Message } from '@/store/useChatStore';
import type { RouteResponse, RouteRequest, Route } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

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
    // Handle the actual backend response format
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
};

/**
 * Format error into a user-friendly message
 */
const formatErrorMessage = (error: unknown): string => {
    if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            return '❌ Не удалось подключиться к серверу. Проверьте, запущен ли бэкенд на порту 8001.';
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
        const requestBody = {
            description: text,
            city: 'astana',
        };

        try {
            const response = await fetch(`${API_BASE_URL}/plan-route`, {
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
