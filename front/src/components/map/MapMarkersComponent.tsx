import React, { useEffect } from 'react';
import { load } from '@2gis/mapgl';
import { Marker } from '@2gis/mapgl/types';
import { useMapStore } from '@/store/useMapStore';

export const MapMarkersComponent: React.FC = () => {
  const { mapInstance } = useMapStore();
  // In a real app, markers would come from props or another store
  // For now we just demo a static marker or markers from a search result store eventually

  useEffect(() => {
    if (!mapInstance) return;

    const markers: Marker[] = [];

    load().then((mapglAPI) => {
      // Example marker
      const marker = new mapglAPI.Marker(mapInstance, {
        coordinates: [37.618423, 55.751244],
        icon: 'https://docs.2gis.com/img/mapgl/marker.svg', // Default 2GIS marker
      });
      markers.push(marker);
    });

    return () => {
      markers.forEach(m => m.destroy());
    };
  }, [mapInstance]);

  return null; // Logic only
};
