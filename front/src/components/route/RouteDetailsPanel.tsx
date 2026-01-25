import React from 'react';
import { useRouteStore } from '@/store/useRouteStore';
import { chatService } from '@/services/chatService';
import { Clock, Route, MapPin, ChevronRight, X, CalendarClock, LogOut, LogIn, Train, Bus, Footprints, ArrowRight } from 'lucide-react';
import type { Route as RouteType, RouteSegmentInfo, RouteWaypoint, PublicTransportMovement } from '@/types';

const { formatDuration, formatDistance } = chatService;

// Get icon for transport type
const getMovementIcon = (movement: PublicTransportMovement) => {
  if (movement.type === 'walkway' || movement.transport_type === 'walk') {
    return <Footprints size={16} className="text-gray-600" />;
  }
  if (movement.transport_type === 'metro') {
    return <Train size={16} className="text-purple-600" />;
  }
  if (movement.transport_type === 'bus' || movement.transport_type === 'trolleybus') {
    return <Bus size={16} className="text-blue-600" />;
  }
  if (movement.transport_type === 'tram') {
    return <Train size={16} className="text-green-600" />;
  }
  return <Bus size={16} className="text-gray-600" />;
};

// Get display name for transport type
const getTransportTypeName = (movement: PublicTransportMovement): string => {
  if (movement.type === 'walkway' || movement.transport_type === 'walk') {
    return 'Пешком';
  }
  const typeMap: Record<string, string> = {
    metro: 'Метро',
    bus: 'Автобус',
    trolleybus: 'Троллейбус',
    tram: 'Трамвай',
    shuttle_bus: 'Маршрутка',
    suburban_train: 'Электричка',
  };
  return typeMap[movement.transport_type || ''] || movement.transport_type || 'Транспорт';
};

interface MovementDisplayProps {
  movement: PublicTransportMovement;
  isLast: boolean;
  index: number;
  isHighlighted: boolean;
  onHover: (index: number | null) => void;
}

const MovementDisplay: React.FC<MovementDisplayProps> = ({ movement, isLast, index, isHighlighted, onHover }) => {
  const durationMinutes = movement.duration_seconds / 60;
  const isWalk = movement.type === 'walkway' || movement.transport_type === 'walk';
  const lineColor = movement.line_color || movement.route_color;

  return (
    <div 
      className={`flex items-start gap-3 py-3 border-b border-gray-100 last:border-b-0 cursor-pointer transition-colors rounded-lg px-2 -mx-2 ${
        isHighlighted ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'
      }`}
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
    >
      {/* Icon and connector line */}
      <div className="flex flex-col items-center">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-transform ${isHighlighted ? 'scale-110' : ''}`}
          style={{
            backgroundColor: lineColor ? `${lineColor}20` : (isWalk ? '#f3f4f6' : '#eff6ff'),
            borderColor: lineColor || (isWalk ? '#9ca3af' : '#3b82f6'),
            borderWidth: isHighlighted ? '3px' : '2px'
          }}
        >
          {getMovementIcon(movement)}
        </div>
        {!isLast && <div className="w-0.5 h-8 bg-gray-200 mt-1" style={lineColor && !isWalk ? { backgroundColor: lineColor } : {}} />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Transport type and route name */}
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-gray-900">
            {getTransportTypeName(movement)}
          </span>
          {(movement.line_name || movement.route_name) && (
            <span
              className="px-2 py-0.5 rounded text-xs font-medium text-white"
              style={{ backgroundColor: lineColor || '#3b82f6' }}
            >
              {movement.line_name || movement.route_name}
            </span>
          )}
        </div>

        {/* From/To stops */}
        {(movement.from_stop || movement.to_stop) && (
          <div className="flex items-center gap-1 mt-1 text-xs text-gray-600">
            <span className="truncate">{movement.from_stop || movement.from_name}</span>
            <ArrowRight size={12} className="flex-shrink-0 text-gray-400" />
            <span className="truncate">{movement.to_stop}</span>
          </div>
        )}

        {/* Direction hint for metro */}
        {movement.direction && (
          <div className="text-xs text-gray-500 mt-1">
            Направление: {movement.direction}
          </div>
        )}

        {/* Stats: distance, time, stops */}
        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {formatDuration(durationMinutes)}
          </span>
          <span className="flex items-center gap-1">
            <Route size={12} />
            {formatDistance(movement.distance_meters)}
          </span>
          {movement.stops_count !== undefined && movement.stops_count > 0 && (
            <span className="flex items-center gap-1">
              📍 {movement.stops_count} {movement.stops_count === 1 ? 'остановка' :
                  movement.stops_count < 5 ? 'остановки' : 'остановок'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

interface SegmentDisplayProps {
  segment: RouteSegmentInfo;
  waypoints: RouteWaypoint[];
  index: number;
}

const SegmentDisplay: React.FC<SegmentDisplayProps> = ({ segment, waypoints, index }) => {
  // Use segment index to get corresponding waypoints (segment N goes from waypoint N to N+1)
  const fromWaypoint = waypoints[index];
  const toWaypoint = waypoints[index + 1];

  const durationMinutes = segment.duration_seconds / 60;

  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-b-0">
      <div className="flex flex-col items-center">
        <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
          {index + 1}
        </div>
        <div className="w-0.5 h-full bg-gray-200 mt-1" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1 text-sm text-gray-600">
          <span className="font-medium truncate">{fromWaypoint?.name || `Точка ${segment.from_waypoint}`}</span>
          <ChevronRight size={14} className="flex-shrink-0 text-gray-400" />
          <span className="font-medium truncate">{toWaypoint?.name || `Точка ${segment.to_waypoint}`}</span>
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Route size={12} />
            {formatDistance(segment.distance_meters)}
          </span>
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {formatDuration(durationMinutes)}
          </span>
        </div>
      </div>
    </div>
  );
};

interface RouteVariantButtonProps {
  route: RouteType;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

const RouteVariantButton: React.FC<RouteVariantButtonProps> = ({ route, index, isSelected, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-shrink-0 min-w-[120px] px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
        isSelected
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      <div className="truncate">{route.title || `Вариант ${index + 1}`}</div>
    </button>
  );
};

export const RouteDetailsPanel: React.FC = () => {
  const { routeResponse, selectedRouteIndex, setSelectedRouteIndex, clearRoute, highlightedMovementIndex, setHighlightedMovementIndex } = useRouteStore();

  if (!routeResponse?.routes?.length) {
    return null;
  }

  const selectedRoute = routeResponse.routes[selectedRouteIndex] || routeResponse.routes[0];
  const hasMultipleRoutes = routeResponse.routes.length > 1;
  const segments = selectedRoute.segments || [];
  const waypoints = selectedRoute.waypoints || [];

  // Generate segments from waypoints if no segments provided
  const displaySegments: RouteSegmentInfo[] = segments.length > 0
    ? segments
    : waypoints.length > 1
      ? waypoints.slice(0, -1).map((wp, idx) => ({
          from_waypoint: wp.order,
          to_waypoint: waypoints[idx + 1].order,
          distance_meters: 0,
          duration_seconds: 0,
        }))
      : [];

  const getTransportIcon = () => {
    const mode = routeResponse.request_summary.transport_mode;
    switch (mode) {
      case 'walking': return '🚶';
      case 'public_transport': return '🚌';
      default: return '🚗';
    }
  };

  return (
    <div className="absolute top-4 left-4 z-30 w-80 max-h-[calc(100vh-180px)] bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 bg-blue-600 text-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin size={18} />
          <span className="font-semibold text-sm">Детали маршрута</span>
        </div>
        <button
          type="button"
          onClick={clearRoute}
          className="p-1 hover:bg-blue-700 rounded-lg transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      {/* Route variants selector */}
      {hasMultipleRoutes && (
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="text-xs text-gray-500 mb-2">Выберите вариант маршрута:</div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {routeResponse.routes.map((route, index) => (
              <RouteVariantButton
                key={route.route_id}
                route={route}
                index={index}
                isSelected={index === selectedRouteIndex}
                onClick={() => setSelectedRouteIndex(index)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Summary stats */}
      <div className="px-4 py-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">{getTransportIcon()}</span>
          <span className="font-medium text-gray-900 text-sm truncate">{selectedRoute.title}</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg p-3 border border-gray-100">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
              <Route size={14} />
              <span>Расстояние</span>
            </div>
            <div className="text-lg font-bold text-gray-900">
              {formatDistance(selectedRoute.total_distance_meters)}
            </div>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-100">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
              <Clock size={14} />
              <span>Время</span>
            </div>
            <div className="text-lg font-bold text-gray-900">
              {formatDuration(selectedRoute.total_duration_minutes)}
            </div>
          </div>
        </div>

        {/* Time-based planning info */}
        {(selectedRoute.recommended_departure_time || selectedRoute.estimated_arrival_time) && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <div className="flex items-center gap-2 text-blue-700 text-xs mb-2">
              <CalendarClock size={14} />
              <span className="font-medium">Планирование по времени</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {selectedRoute.recommended_departure_time && (
                <div className="flex items-center gap-2">
                  <LogOut size={14} className="text-blue-600" />
                  <div>
                    <div className="text-xs text-gray-500">Выезд</div>
                    <div className="text-sm font-bold text-gray-900">{selectedRoute.recommended_departure_time}</div>
                  </div>
                </div>
              )}
              {selectedRoute.estimated_arrival_time && (
                <div className="flex items-center gap-2">
                  <LogIn size={14} className="text-green-600" />
                  <div>
                    <div className="text-xs text-gray-500">Прибытие</div>
                    <div className="text-sm font-bold text-gray-900">{selectedRoute.estimated_arrival_time}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Public transport specific info */}
        {selectedRoute.transport_chain && (
          <div className="mt-3 p-3 bg-white rounded-lg border border-gray-100">
            <div className="text-xs text-gray-500 mb-1">Маршрут транспорта:</div>
            <div className="text-sm font-medium text-gray-900">{selectedRoute.transport_chain}</div>
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
              {selectedRoute.transfer_count !== undefined && (
                <span>🔄 Пересадок: {selectedRoute.transfer_count}</span>
              )}
              {selectedRoute.walking_duration_minutes !== undefined && (
                <span>🚶 Пешком: {formatDuration(selectedRoute.walking_duration_minutes)}</span>
              )}
              {selectedRoute.schedule?.departure_time && (
                <span>🕐 Отправление: {selectedRoute.schedule.departure_time}</span>
              )}
              {selectedRoute.schedule?.period_minutes && (
                <span>⏱️ Интервал: {selectedRoute.schedule.period_minutes} мин</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Public transport movements */}
      {selectedRoute.movements && selectedRoute.movements.length > 0 ? (
        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="text-xs text-gray-500 mb-2">Этапы маршрута: <span className="text-gray-400">(наведите для подсветки на карте)</span></div>
          {selectedRoute.movements.map((movement, index) => (
            <MovementDisplay
              key={`movement-${index}`}
              movement={movement}
              index={index}
              isLast={index === selectedRoute.movements!.length - 1}
              isHighlighted={highlightedMovementIndex === index}
              onHover={setHighlightedMovementIndex}
            />
          ))}
        </div>
      ) : displaySegments.length > 0 && displaySegments.some(s => s.distance_meters > 0 || s.duration_seconds > 0) ? (
        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="text-xs text-gray-500 mb-2">Сегменты маршрута:</div>
          {displaySegments.map((segment, index) => (
            <SegmentDisplay
              key={`${segment.from_waypoint}-${segment.to_waypoint}`}
              segment={segment}
              waypoints={waypoints}
              index={index}
            />
          ))}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <div className="text-xs text-gray-500 mb-2">Точки маршрута:</div>
          {waypoints.map((waypoint, index) => (
            <div key={waypoint.order} className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-b-0">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                waypoint.type === 'start'
                  ? 'bg-green-100 text-green-600'
                  : waypoint.type === 'end'
                    ? 'bg-red-100 text-red-600'
                    : 'bg-blue-100 text-blue-600'
              }`}>
                {waypoint.type === 'start' ? 'А' : waypoint.type === 'end' ? 'Б' : index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">{waypoint.name}</div>
                <div className="text-xs text-gray-500 truncate">{waypoint.address}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
