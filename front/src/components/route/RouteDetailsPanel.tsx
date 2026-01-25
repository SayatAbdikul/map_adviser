import React from 'react';
import { useRouteStore } from '@/store/useRouteStore';
import { chatService } from '@/services/chatService';
import { Clock, Route, MapPin, ChevronRight, X } from 'lucide-react';
import type { Route as RouteType, RouteSegmentInfo, RouteWaypoint } from '@/types';

const { formatDuration, formatDistance } = chatService;

interface SegmentDisplayProps {
  segment: RouteSegmentInfo;
  waypoints: RouteWaypoint[];
  index: number;
}

const SegmentDisplay: React.FC<SegmentDisplayProps> = ({ segment, waypoints, index }) => {
  const fromWaypoint = waypoints.find(w => w.order === segment.from_waypoint);
  const toWaypoint = waypoints.find(w => w.order === segment.to_waypoint);

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
  const { routeResponse, selectedRouteIndex, setSelectedRouteIndex, clearRoute } = useRouteStore();

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

        {/* Public transport specific info */}
        {selectedRoute.transport_chain && (
          <div className="mt-3 p-3 bg-white rounded-lg border border-gray-100">
            <div className="text-xs text-gray-500 mb-1">Маршрут транспорта:</div>
            <div className="text-sm font-medium text-gray-900">{selectedRoute.transport_chain}</div>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              {selectedRoute.transfer_count !== undefined && (
                <span>🔄 Пересадок: {selectedRoute.transfer_count}</span>
              )}
              {selectedRoute.walking_duration_minutes !== undefined && (
                <span>🚶 Пешком: {formatDuration(selectedRoute.walking_duration_minutes)}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Segments list */}
      {displaySegments.length > 0 && displaySegments.some(s => s.distance_meters > 0 || s.duration_seconds > 0) ? (
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
