import { API_BASE_URL, buildApiUrl } from '@/constants';
import type { Message } from '@/store/useChatStore';
import type {
    ChatHistoryItem,
    ClarificationResponse,
    CoreAgentResponse,
    LegacyRouteResponse,
    RouteRequest,
    RouteResponse,
} from '@/types';
import { isClarificationResponse } from '@/types';

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

const formatTransportMode = (mode: string | null | undefined): string | null => {
    if (!mode) return null;
    const labels: Record<string, string> = {
        driving: 'на машине',
        walking: 'пешком',
        public_transport: 'общественный транспорт',
    };
    return labels[mode] || mode;
};

const formatOptimizationChoice = (choice: string | null | undefined): string | null => {
    if (!choice) return null;
    const labels: Record<string, string> = {
        distance: 'по расстоянию',
        time: 'по времени',
    };
    return labels[choice] || choice;
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
        const summary = response.request_summary;

        lines.push('🗺️ Маршрут построен успешно!');
        if (summary?.intent) {
            lines.push(`🎯 ${summary.intent}`);
        }
        if (summary?.origin_address) {
            lines.push(`📍 Старт: ${summary.origin_address}`);
        }
        const modeLabel = formatTransportMode(summary?.transport_mode);
        if (modeLabel) {
            lines.push(`🧭 Режим: ${modeLabel}`);
        }
        const optimizationLabel = formatOptimizationChoice(summary?.optimization_choice);
        if (optimizationLabel) {
            lines.push(`⚙️ Оптимизация: ${optimizationLabel}`);
        }
        if (summary?.arrival_time) {
            lines.push(`⏰ Время прибытия: ${summary.arrival_time}`);
        }
        if (summary?.departure_time) {
            lines.push(`🕒 Рекомендуемое отправление: ${summary.departure_time}`);
        }

        lines.push('');

        const primaryRoute = routes[0];
        const waypoints = [...(primaryRoute.waypoints || [])].sort(
            (a, b) => a.order - b.order
        );

        lines.push(`🛣️ ${primaryRoute.title || 'Основной маршрут'}`);
        lines.push(`📏 Общее расстояние: ${formatDistance(primaryRoute.total_distance_meters ?? null)}`);
        lines.push(`⏱️ Время в пути: ${formatDuration(primaryRoute.total_duration_minutes ?? null)}`);
        
        if (primaryRoute.transport_chain) {
            lines.push(`🚌 ${primaryRoute.transport_chain}`);
        }
        
        if (primaryRoute.transfer_count !== undefined) {
            lines.push(`🔄 Пересадок: ${primaryRoute.transfer_count}`);
        }
        
        lines.push('');

        // Waypoints list
        if (waypoints.length > 0) {
            lines.push('📍 Точки маршрута:');
            waypoints.forEach((waypoint, index) => {
                const name = waypoint.name || `Точка ${index + 1}`;
                const address = waypoint.address ? ` — ${waypoint.address}` : '';
                lines.push(`${index + 1}. ${name}${address}`);
            });
        }

        // Show route options if multiple
        if (routes.length > 1) {
            lines.push('');
            lines.push('🗺️ Варианты маршрута:');
            routes.forEach((route, index) => {
                const distance = formatDistance(route.total_distance_meters ?? null);
                const duration = formatDuration(route.total_duration_minutes ?? null);
                lines.push(`${index + 1}. ${route.title || `Вариант ${index + 1}`} — ${distance}, ${duration}`);
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
    clarification?: ClarificationResponse;
}

export const chatService = {
    /**
     * Send a route query to the backend
     */
    sendMessage: async (
        text: string,
        mode: 'driving' | 'walking' | 'public_transport' = 'driving',
        history: ChatHistoryItem[] = [],
    ): Promise<ChatServiceResponse> => {
        const requestBody: RouteRequest = {
            query: text,
            mode,
            history,
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

            const routeResponse: RouteResponse | ClarificationResponse = await response.json();

            // Clarification branch
            if (isClarificationResponse(routeResponse)) {
                return {
                    message: {
                        id: Date.now().toString(),
                        text: routeResponse.question,
                        sender: 'bot',
                        timestamp: Date.now(),
                    },
                    routeData: null,
                    clarification: routeResponse,
                };
            }

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
