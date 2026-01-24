import React, { useEffect, useRef } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';
import { MapControls } from './MapControls';
import { MapMarkersComponent } from './MapMarkersComponent';

const API_KEY = import.meta.env.VITE_2GIS_API_KEY;

export const MapContainer: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const { setMapInstance, setCenter, setZoom, centeryb, zoom } = useMapStore();

  useEffect(() => {
    let map: MapGL | null = null;

    if (mapContainerRef.current) {
      load().then((mapglAPI) => {
        map = new mapglAPI.Map(mapContainerRef.current!, {
          center: centeryb,
          zoom: zoom,
          key: API_KEY, 
          zoomControl: false,
        });

        setMapInstance(map);

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
