import React, { useEffect, useMemo, useRef, useState } from 'react';
import { load } from '@2gis/mapgl';
import type { Marker } from '@2gis/mapgl/types';
import { X } from 'lucide-react';
import { Card } from '@/components/common/Card';
import { useMapStore } from '@/store/useMapStore';
import { useRouteStore } from '@/store/useRouteStore';
import type { Route, RouteWaypoint, CoreRoute } from '@/types';
import { isCoreAgentResponse } from '@/types';

type TransportMode = 'driving' | 'walking' | 'public_transport';

const ROUTE_COLORS = ['#2563eb', '#f97316', '#16a34a', '#db2777', '#eab308'];

const MARKER_COLORS: Record<string, string> = {
  start: '#22c55e',
  stop: '#3b82f6',
  end: '#ef4444',
};

const MODE_ACCENT: Record<
  TransportMode,
  { color: string; label: string; name: string }
> = {
  driving: { color: '#2563eb', label: 'D', name: 'Driving' },
  walking: { color: '#16a34a', label: 'W', name: 'Walking' },
  public_transport: { color: '#f97316', label: 'B', name: 'Public transport' },
};

const createMarkerIcon = (
  fillColor: string,
  ringColor: string,
  label: string
) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
    <circle cx="17" cy="17" r="15" fill="${fillColor}" stroke="${ringColor}" stroke-width="4" />
    <text x="17" y="21" text-anchor="middle" font-size="10" font-family="Arial, sans-serif" fill="#ffffff">${label}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
};

const getWaypointCoordinates = (
  waypoint: RouteWaypoint
): [number, number] | null => {
  const lon = waypoint.location?.lon ?? waypoint.lon;
  const lat = waypoint.location?.lat ?? waypoint.lat;
  if (typeof lon !== 'number' || typeof lat !== 'number') return null;
  return [lon, lat];
};

const toTransportMode = (
  route: Route,
  fallback?: string | null
): TransportMode => {
  if (route.transport_chain) return 'public_transport';
  if (
    fallback === 'walking' ||
    fallback === 'public_transport' ||
    fallback === 'driving'
  ) {
    return fallback;
  }
  return 'driving';
};

type ActiveWaypoint = {
  route: Route;
  waypoint: RouteWaypoint;
  mode: TransportMode;
  routeColor: string;
};

export const MapMarkersComponent: React.FC = () => {
  const { mapInstance } = useMapStore();
  const { routeResponse, selectedRouteIndex } = useRouteStore();
  console.log('routeResponse', routeResponse);
  const [activeWaypoint, setActiveWaypoint] = useState<ActiveWaypoint | null>(
    null
  );
  const mapglRef = useRef<Awaited<ReturnType<typeof load>> | null>(null);

  // Handle different response formats
  const routes = routeResponse && isCoreAgentResponse(routeResponse) 
    ? routeResponse.routes ?? [] 
    : [];
  
  console.log('routes', routes);
  const requestMode = routeResponse && isCoreAgentResponse(routeResponse)
    ? routeResponse.request_summary?.transport_mode ?? null
    : null;

  const colorById = useMemo(
    () =>
      new Map(
        routes.map((route: CoreRoute, index: number) => [
          route.route_id,
          ROUTE_COLORS[index % ROUTE_COLORS.length],
        ])
      ),
    [routes]
  );

  useEffect(() => {
    setActiveWaypoint(null);
  }, [routes, selectedRouteIndex]);

  useEffect(() => {
    if (!mapInstance) return;

    const markers: Marker[] = [];
    let isMounted = true;

    const renderMarkers = async () => {
      if (routes.length === 0) return;
      if (!mapglRef.current) {
        mapglRef.current = await load();
      }
      const mapglAPI = mapglRef.current;
      if (!mapglAPI || !isMounted) return;

      routes.forEach((route: CoreRoute, index: number) => {
        const orderedWaypoints = [...(route.waypoints ?? [])].sort(
          (a, b) => a.order - b.order
        );
        const routeColor: string =
          colorById.get(route.route_id) ??
          ROUTE_COLORS[index % ROUTE_COLORS.length];
        const mode = toTransportMode(route, requestMode);
        const modeAccent = MODE_ACCENT[mode];
        const isSelected = index === selectedRouteIndex;

        orderedWaypoints.forEach(waypoint => {
          const coords = getWaypointCoordinates(waypoint);
          if (!coords) return;
          const fillColor = MARKER_COLORS[waypoint.type] ?? MARKER_COLORS.stop;
          const marker = new mapglAPI.Marker(mapInstance, {
            coordinates: coords,
            icon: createMarkerIcon(
              fillColor,
              modeAccent.color,
              modeAccent.label
            ),
            size: [34, 34],
            anchor: [17, 17],
            zIndex: isSelected ? 3 : 1,
            label: {
              text: waypoint.name,
              color: '#0f172a',
              fontSize: 12,
              haloRadius: 6,
              haloColor: '#ffffff',
              offset: [0, -28],
            },
            interactive: true,
          });
          marker.on('click', () => {
            setActiveWaypoint({
              route,
              waypoint,
              mode,
              routeColor,
            });
          });
          markers.push(marker);
        });
      });
    };

    renderMarkers();

    return () => {
      isMounted = false;
      markers.forEach(m => m.destroy());
    };
  }, [mapInstance, routes, requestMode, selectedRouteIndex, colorById]);

  if (!activeWaypoint) return null;

  const modeAccent = MODE_ACCENT[activeWaypoint.mode];

  return (
    <div className="absolute left-4 top-4 z-20 w-72">
      <Card className="app-shadow">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold app-text">
              {activeWaypoint.waypoint.name}
            </div>
            <div className="text-xs app-muted mt-1">
              {activeWaypoint.waypoint.address}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setActiveWaypoint(null)}
            className="text-[color:var(--app-muted)] hover:text-[color:var(--app-text)]"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-[color:var(--app-muted)]">
          <span
            className="inline-flex h-2 w-2 rounded-full"
            style={{ backgroundColor: activeWaypoint.routeColor }}
          />
          <span>{activeWaypoint.route.title}</span>
        </div>
        <div className="mt-2 text-xs text-[color:var(--app-muted)] flex items-center gap-2">
          <span
            className="inline-flex h-2 w-2 rounded-full"
            style={{ backgroundColor: modeAccent.color }}
          />
          <span>Mode: {modeAccent.name}</span>
        </div>
        {activeWaypoint.waypoint.category && (
          <div className="mt-2">
            <span className="inline-flex items-center rounded-full bg-[color:var(--app-surface-2)] px-2 py-0.5 text-xs font-medium text-[color:var(--app-muted)]">
              {activeWaypoint.waypoint.category}
            </span>
          </div>
        )}
      </Card>
    </div>
  );
};
