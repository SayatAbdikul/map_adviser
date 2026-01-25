import React, { useEffect, useRef, useState } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL, Polyline, Marker } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';
import { useRouteStore } from '@/store/useRouteStore';
import { MapControls } from './MapControls';
import { MapMarkersComponent } from './MapMarkersComponent';
import { RouteDetailsPanel } from '../route/RouteDetailsPanel';

const API_KEY = import.meta.env.VITE_2GIS_API_KEY;

export const MapContainer: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapGL | null>(null);
  const mapglRef = useRef<Awaited<ReturnType<typeof load>> | null>(null);
  const routeRefs = useRef<Polyline[]>([]);
  const markerRefs = useRef<Marker[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const { setMapInstance, setCenter, setZoom, centeryb, zoom } = useMapStore();
  const { routeResponse, selectedRouteIndex } = useRouteStore();

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
      if (markerRefs.current.length > 0) {
        markerRefs.current.forEach(marker => marker.destroy());
        markerRefs.current = [];
      }
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
        setMapInstance(null);
      }
    };
  }, []);

  // Render route when routeResponse changes
  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapglRef.current) return;

    // Clear existing routes and markers
    if (routeRefs.current.length > 0) {
      routeRefs.current.forEach(route => route.destroy());
      routeRefs.current = [];
    }
    if (markerRefs.current.length > 0) {
      markerRefs.current.forEach(marker => marker.destroy());
      markerRefs.current = [];
    }

    // Check if we have route data
    if (!routeResponse?.routes?.length) return;

    const selectedRoute = routeResponse.routes[selectedRouteIndex] || routeResponse.routes[0];
    if (!selectedRoute) return;

    // Draw all route geometries - non-selected first (transparent), then selected (solid)
    // First pass: draw non-selected routes with transparent color (using RGBA)
    routeResponse.routes.forEach((route, index) => {
      if (index === selectedRouteIndex) return; // Skip selected route for now
      if (route.route_geometry && route.route_geometry.length > 1) {
        const polyline = new mapglRef.current!.Polyline(mapRef.current!, {
          coordinates: route.route_geometry,
          width: 5,
          color: 'rgba(37, 99, 235, 0.35)',
        });
        routeRefs.current.push(polyline);
      }
    });

    // Second pass: draw selected route on top with solid color
    if (selectedRoute.route_geometry && selectedRoute.route_geometry.length > 1) {
      const polyline = new mapglRef.current!.Polyline(mapRef.current!, {
        coordinates: selectedRoute.route_geometry,
        width: 6,
        color: '#2563eb',
      });
      routeRefs.current.push(polyline);
    }

    // Add waypoint markers for selected route
    if (selectedRoute.waypoints && selectedRoute.waypoints.length > 0) {
      const waypoints = selectedRoute.waypoints;
      
      waypoints.forEach((waypoint, index) => {
        const isStart = waypoint.type === 'start';
        const isEnd = waypoint.type === 'end';
        
        // Get coordinates from location object
        const lon = waypoint.location?.lon ?? waypoint.lon;
        const lat = waypoint.location?.lat ?? waypoint.lat;
        
        if (lon === undefined || lat === undefined) return;
        
        const marker = new mapglRef.current!.Marker(mapRef.current!, {
          coordinates: [lon, lat],
          label: {
            text: isStart ? 'А' : isEnd ? 'Б' : `${index + 1}`,
            offset: [0, -45],
            fontSize: 14,
            color: '#ffffff',
          },
        });
        markerRefs.current.push(marker);
      });

      // Fit map to show all waypoints
      if (waypoints.length >= 2) {
        const coords = waypoints
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
          
          mapRef.current.setCenter([centerLon, centerLat]);
          
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
          
          mapRef.current.setZoom(newZoom);
        }
      }
    }
  }, [mapReady, routeResponse, selectedRouteIndex]);

  return (
    <div className="relative w-full h-full bg-gray-200">
      <div ref={mapContainerRef} className="w-full h-full" />
      <RouteDetailsPanel />
      <MapControls />
      <MapMarkersComponent />
    </div>
  );
};
