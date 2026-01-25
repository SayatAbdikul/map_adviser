import React, { useEffect, useRef, useState } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL, Polyline, Marker } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';
import { useRouteStore } from '@/store/useRouteStore';
import { useRoomStore } from '@/store/useRoomStore';
import { MapControls } from './MapControls';
import { MapMarkersComponent } from './MapMarkersComponent';
import { RouteDetailsPanel } from '../route/RouteDetailsPanel';
import type { Route, PublicTransportMovement } from '@/types';
import { RoomPanel, MemberMarkers } from '../room';

const API_KEY = import.meta.env.VITE_2GIS_API_KEY;
const ROUTE_COLORS = ['#2563eb', '#f97316', '#16a34a'];
const WALKING_COLOR = '#6b7280'; // Gray for walking segments
const DEFAULT_TRANSIT_COLOR = '#3b82f6'; // Blue fallback

// Check if movement is a walking segment
const isWalkingMovement = (movement: PublicTransportMovement): boolean => {
  return movement.type === 'walkway' || movement.transport_type === 'walk';
};

// Get color for a movement segment
const getMovementColor = (movement: PublicTransportMovement): string => {
  if (isWalkingMovement(movement)) {
    return WALKING_COLOR;
  }
  return movement.line_color || movement.route_color || DEFAULT_TRANSIT_COLOR;
};

// Get route geometry from route_geometry or build from movements/waypoints
const getRouteGeometry = (route: Route): [number, number][] => {
  // First try route_geometry
  if (route.route_geometry && route.route_geometry.length > 1) {
    return route.route_geometry;
  }

  // For public transport, try to build from movements
  if (route.movements && route.movements.length > 0) {
    const geometry: [number, number][] = [];
    for (const movement of route.movements) {
      if (movement.geometry && movement.geometry.length > 0) {
        geometry.push(...movement.geometry);
      }
    }
    if (geometry.length > 1) {
      return geometry;
    }
  }

  // Fallback: connect waypoints with straight lines
  if (route.waypoints && route.waypoints.length > 1) {
    return route.waypoints
      .map(w => {
        const lon = w.location?.lon ?? w.lon;
        const lat = w.location?.lat ?? w.lat;
        return (lon !== undefined && lat !== undefined) ? [lon, lat] as [number, number] : null;
      })
      .filter((c): c is [number, number] => c !== null);
  }

  return [];
};

export const MapContainer: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapGL | null>(null);
  const mapglRef = useRef<Awaited<ReturnType<typeof load>> | null>(null);
  const routeRefs = useRef<Polyline[]>([]);
  const transferMarkerRefs = useRef<Marker[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const { setMapInstance, setCenter, setZoom, centeryb, zoom } = useMapStore();
  const { routeResponse, selectedRouteIndex, highlightedMovementIndex } = useRouteStore();
  const { isManualLocationMode, isConnected, updateMyLocation, setManualLocationMode } = useRoomStore();

  // Initialize map
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
      if (transferMarkerRefs.current.length > 0) {
        transferMarkerRefs.current.forEach(marker => marker.destroy());
        transferMarkerRefs.current = [];
      }
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
        setMapInstance(null);
      }
    };
  }, []);

  // Handle map clicks for manual location mode
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    const handleMapClick = (e: { lngLat: number[] }) => {
      if (isManualLocationMode && isConnected) {
        const [lon, lat] = e.lngLat;
        updateMyLocation({
          lat,
          lon,
          heading: null,
          accuracy: null,
        });
        // Turn off manual mode after setting location
        setManualLocationMode(false);
      }
    };

    mapRef.current.on('click', handleMapClick as (ev: unknown) => void);

    return () => {
      if (mapRef.current) {
        mapRef.current.off('click', handleMapClick as (ev: unknown) => void);
      }
    };
  }, [mapReady, isManualLocationMode, isConnected, updateMyLocation, setManualLocationMode]);

  // Render route when routeResponse changes
  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapglRef.current) return;

    // Clear existing routes and markers
    if (routeRefs.current.length > 0) {
      routeRefs.current.forEach(route => route.destroy());
      routeRefs.current = [];
    }
    if (transferMarkerRefs.current.length > 0) {
      transferMarkerRefs.current.forEach(marker => marker.destroy());
      transferMarkerRefs.current = [];
    }

    // Check if we have route data
    if (!routeResponse?.routes?.length) return;

    const routes = routeResponse.routes;
    const selectedRoute = routes[selectedRouteIndex] || routes[0];
    if (!selectedRoute) return;

    const isPublicTransport = routeResponse.request_summary.transport_mode === 'public_transport';

    // Draw all route geometries - non-selected first (transparent), then selected (solid)
    // First pass: draw non-selected routes with transparent color (using RGBA)
    routeResponse.routes.forEach((route, index) => {
      if (index === selectedRouteIndex) return; // Skip selected route for now
      const geometry = getRouteGeometry(route);
      if (geometry.length > 1) {
        const polyline = new mapglRef.current!.Polyline(mapRef.current!, {
          coordinates: geometry,
          width: 5,
          color: 'rgba(37, 99, 235, 0.35)',
        });
        routeRefs.current.push(polyline);
      }
    });

    // Second pass: draw selected route
    // For public transport with movements, draw per-segment colored polylines
    if (isPublicTransport && selectedRoute.movements && selectedRoute.movements.length > 0) {
      console.log('[MapContainer] Drawing public transport movements:', selectedRoute.movements.length);
      
      selectedRoute.movements.forEach((movement, movementIndex) => {
        if (!movement.geometry || movement.geometry.length < 2) {
          console.log(`[MapContainer] Movement ${movementIndex} has no geometry or < 2 points`);
          return;
        }
        
        const isWalking = isWalkingMovement(movement);
        const color = getMovementColor(movement);
        const isHighlighted = highlightedMovementIndex === movementIndex;
        
        console.log(`[MapContainer] Drawing segment ${movementIndex}: type=${movement.type}, transport=${movement.transport_type}, color=${color}, walking=${isWalking}, points=${movement.geometry.length}`);
        
        // For walking segments, draw a dashed line
        if (isWalking) {
          // Draw dashed polyline for walking
          const dashedPolyline = new mapglRef.current!.Polyline(mapRef.current!, {
            coordinates: movement.geometry,
            width: isHighlighted ? 7 : 5,
            color: WALKING_COLOR,
            dashLength: 12,
            gapLength: 8,
          });
          routeRefs.current.push(dashedPolyline);
        } else {
          // Draw solid polyline for transit
          const polyline = new mapglRef.current!.Polyline(mapRef.current!, {
            coordinates: movement.geometry,
            width: isHighlighted ? 9 : 6,
            color: color,
          });
          routeRefs.current.push(polyline);
        }
      });
      
      // Add transfer point markers - use first/last points of transit segments
      console.log('[MapContainer] Adding transfer markers');
      selectedRoute.movements.forEach((movement, movementIndex) => {
        if (!movement.geometry || movement.geometry.length === 0) return;
        if (isWalkingMovement(movement)) return; // Skip walking segments
        
        const startCoord = movement.geometry[0] as [number, number];
        const endCoord = movement.geometry[movement.geometry.length - 1] as [number, number];
        const fromName = movement.from_stop || movement.from_name || '';
        const toName = movement.to_stop || '';
        const lineColor = movement.line_color || movement.route_color || DEFAULT_TRANSIT_COLOR;
        
        console.log(`[MapContainer] Transit segment ${movementIndex}: from="${fromName}" at [${startCoord}], to="${toName}" at [${endCoord}]`);
        
        // Add start marker (boarding point)
        if (startCoord && startCoord.length === 2) {
          const startMarker = new mapglRef.current!.Marker(mapRef.current!, {
            coordinates: startCoord,
            icon: 'data:image/svg+xml;base64,' + btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" fill="${lineColor}" stroke="white" stroke-width="2"/></svg>`),
            size: [14, 14],
            anchor: [7, 7],
          });
          transferMarkerRefs.current.push(startMarker);
        }
        
        // Add end marker (alighting point)
        if (endCoord && endCoord.length === 2 && toName) {
          const endMarker = new mapglRef.current!.Marker(mapRef.current!, {
            coordinates: endCoord,
            icon: 'data:image/svg+xml;base64,' + btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" fill="${lineColor}" stroke="white" stroke-width="2"/></svg>`),
            size: [14, 14],
            anchor: [7, 7],
          });
          transferMarkerRefs.current.push(endMarker);
        }
      });
    } else {
      // For driving/walking, draw single colored polyline as before
      const selectedGeometry = getRouteGeometry(selectedRoute);
      if (selectedGeometry.length > 1) {
        const polyline = new mapglRef.current!.Polyline(mapRef.current!, {
          coordinates: selectedGeometry,
          width: 7,
          color: ROUTE_COLORS[selectedRouteIndex % ROUTE_COLORS.length],
        });
        routeRefs.current.push(polyline);
      }
    }

    // Fit map to show all waypoints
    if (selectedRoute.waypoints && selectedRoute.waypoints.length > 1) {
      const coords = selectedRoute.waypoints
        .map(w => {
          const lon = w.location?.lon ?? w.lon;
          const lat = w.location?.lat ?? w.lat;
          return lon !== undefined && lat !== undefined ? { lon, lat } : null;
        })
        .filter((c): c is { lon: number; lat: number } => c !== null);
      
      if (coords.length >= 2) {
        const lons = coords.map(c => c.lon);
        const lats = coords.map(c => c.lat);
        const minLon = Math.min(...lons);
        const maxLon = Math.max(...lons);
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        
        const centerLon = (minLon + maxLon) / 2;
        const centerLat = (minLat + maxLat) / 2;
        
        mapRef.current!.setCenter([centerLon, centerLat]);
        
        // Calculate appropriate zoom level
        const lonDiff = maxLon - minLon;
        const latDiff = maxLat - minLat;
        const maxDiff = Math.max(lonDiff, latDiff);
        
        let newZoom = 14;
        if (maxDiff > 0.1) newZoom = 11;
        else if (maxDiff > 0.05) newZoom = 12;
        else if (maxDiff > 0.02) newZoom = 13;
        else if (maxDiff > 0.01) newZoom = 14;
        else newZoom = 15;
        
        mapRef.current!.setZoom(newZoom);
      }
    }
  }, [mapReady, routeResponse, selectedRouteIndex, highlightedMovementIndex]);

  return (
    <div className="relative w-full h-full app-surface-2">
      <div 
        ref={mapContainerRef} 
        className={`w-full h-full ${isManualLocationMode ? 'cursor-crosshair' : ''}`} 
      />
      {isManualLocationMode && (
        <div className="absolute top-1/2 left-1/2 z-10 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          <div className="rounded-full app-accent px-4 py-2 text-sm font-medium app-shadow animate-pulse">
            Click anywhere to set your location
          </div>
        </div>
      )}
      <RouteDetailsPanel />
      <MapControls />
      <MapMarkersComponent />
      <RoomPanel />
      {mapReady && mapRef.current && <MemberMarkers map={mapRef.current} />}
    </div>
  );
};
