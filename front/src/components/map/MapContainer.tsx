import React, { useEffect, useRef } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL, Polyline } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';
import { MapControls } from './MapControls';
import { MapMarkersComponent } from './MapMarkersComponent';

const API_KEY = import.meta.env.VITE_2GIS_API_KEY;

const MOCK_ROUTE: [number, number][] = [
  [37.60305783309946, 55.760320563290726],
  [37.61890514654442, 55.76235858700707],
  // [76.8972, 43.2474],
  // [76.9038, 43.2522],
  // [76.9104, 43.2561],
];

export const MapContainer: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const { setMapInstance, setCenter, setZoom, centeryb, zoom } = useMapStore();

  useEffect(() => {
    let map: MapGL | null = null;
    let route: Polyline | null = null;

    if (mapContainerRef.current) {
      load().then(mapglAPI => {
        map = new mapglAPI.Map(mapContainerRef.current!, {
          center: centeryb,
          zoom: zoom,
          key: API_KEY,
          zoomControl: false,
        });

        setMapInstance(map);

        // Draw mock route
        route = new mapglAPI.Polyline(map, {
          coordinates: MOCK_ROUTE,
          width: 6,
          color: '#3b82f6',
        });

        // Event listeners
        map.on('moveend', () => {
          if (!map) return;
          const center = map.getCenter();
          const zoom = map.getZoom();
          if (center && Array.isArray(center) && center.length === 2) {
            setCenter(center as [number, number]);
          }
          setZoom(zoom);
        });
      });
    }

    return () => {
      if (route) {
        route.destroy();
      }
      if (map) {
        map.destroy();
        setMapInstance(null);
      }
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-gray-200">
      <div ref={mapContainerRef} className="w-full h-full" />
      <MapControls />
      <MapMarkersComponent />
    </div>
  );
};
