import React, { useEffect, useRef, useState } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL, Polyline } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';
import { MapControls } from './MapControls';
import { MapMarkersComponent } from './MapMarkersComponent';

const API_KEY = import.meta.env.VITE_2GIS_API_KEY;
const API_BASE_URL = 'http://localhost:8000/api';

const ROUTE_POINTS = [
  { lat: 55.76032056329073, lon: 37.60305783309946 },
  { lat: 55.76235858700707, lon: 37.61890514654442 },
  { lat: 55.767992, lon: 37.61364 },
  { lat: 55.758825, lon: 37.620053 },
  { lat: 55.75484477885921, lon: 37.59803940836207 },
];

const parseLineString = (wkt: string): [number, number][] => {
  const match = wkt.match(/LINESTRING\((.*)\)/);
  if (!match) return [];

  return match[1]
    .split(',')
    .map(pair => {
      const [lon, lat] = pair.trim().split(/\s+/).map(Number);
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
      return [lon, lat] as [number, number];
    })
    .filter((point): point is [number, number] => point !== null);
};

const SEGMENT_COLORS: Record<string, string> = {
  fast: '#16a34a',
  normal: '#2563eb',
  slow: '#dc2626',
  ignore: '#9ca3af',
};

type RouteSegment = {
  coords: [number, number][];
  color: string;
};

type RouteGeometrySegment = {
  selection: string;
  color?: string;
};

type RouteManeuver = {
  outcoming_path?: {
    geometry?: RouteGeometrySegment[];
  };
};

type RoutingApiResponse = {
  result?: Array<{
    maneuvers?: RouteManeuver[];
  }>;
};

const extractRouteSegments = (data: RoutingApiResponse): RouteSegment[] => {
  const maneuvers = data.result?.[0]?.maneuvers ?? [];

  return maneuvers
    .flatMap(maneuver =>
      (maneuver.outcoming_path?.geometry ?? []).map(segment => {
      const coords = parseLineString(segment.selection);
      const color = SEGMENT_COLORS[segment.color!] ?? '#2563eb';
      return { coords, color };
      })
    )
    .filter(segment => segment.coords.length > 0);
};

export const MapContainer: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapGL | null>(null);
  const mapglRef = useRef<Awaited<ReturnType<typeof load>> | null>(null);
  const routeRefs = useRef<Polyline[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const [routeSegments, setRouteSegments] = useState<RouteSegment[]>([]);
  const { setMapInstance, setCenter, setZoom, centeryb, zoom } = useMapStore();

  useEffect(() => {
    let isMounted = true;

    if (mapContainerRef.current) {
      load().then(mapglAPI => {
        if (!isMounted) return;

        mapglRef.current = mapglAPI;
        mapRef.current = new mapglAPI.Map(mapContainerRef.current!, {
          center: centeryb,
          zoom: zoom,
          key: API_KEY,
          zoomControl: false,
        });

        setMapInstance(mapRef.current);
        setMapReady(true);

        mapRef.current.on('moveend', () => {
          if (!mapRef.current) return;
          const center = mapRef.current.getCenter();
          const nextZoom = mapRef.current.getZoom();
          if (center && Array.isArray(center) && center.length === 2) {
            setCenter(center as [number, number]);
          }
          setZoom(nextZoom);
        });
      });
    }

    return () => {
      isMounted = false;
      if (routeRefs.current.length > 0) {
        routeRefs.current.forEach(route => route.destroy());
        routeRefs.current = [];
      }
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
        setMapInstance(null);
      }
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    const fetchRoute = async () => {
      const params = new URLSearchParams();
      ROUTE_POINTS.forEach(point => {
        params.append('points', `${point.lat},${point.lon}`);
      });
      params.append('mode', 'car');

      const response = await fetch(`${API_BASE_URL}/directions?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!response.ok) return;
      const data = (await response.json()) as RoutingApiResponse;
      const segments = extractRouteSegments(data);
      setRouteSegments(segments);
    };

    fetchRoute();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapglRef.current || routeSegments.length === 0) return;

    if (routeRefs.current.length > 0) {
      routeRefs.current.forEach(route => route.destroy());
      routeRefs.current = [];
    }

    routeRefs.current = routeSegments.map(segment => {
      return new mapglRef.current!.Polyline(mapRef.current!, {
        coordinates: segment.coords,
        width: 6,
        color: segment.color,
      });
    });
  }, [mapReady, routeSegments]);

  return (
    <div className="relative w-full h-full bg-gray-200">
      <div ref={mapContainerRef} className="w-full h-full" />
      <MapControls />
      <MapMarkersComponent />
    </div>
  );
};
