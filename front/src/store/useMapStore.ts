import { create } from 'zustand';
import { Map as MapGL } from '@2gis/mapgl/types';

interface MapState {
  mapInstance: MapGL | null;
  centeryb: [number, number];
  zoom: number;
  setMapInstance: (map: MapGL | null) => void;
  setCenter: (center: [number, number]) => void;
  setZoom: (zoom: number) => void;
}

export const useMapStore = create<MapState>((set) => ({
  mapInstance: null,
  centeryb: [37.60305783309946, 55.760320563290726], // Astana coordinates as default
  zoom: 13,
  setMapInstance: (map) => set({ mapInstance: map }),
  setCenter: (center) => set({ centeryb: center }),
  setZoom: (zoom) => set({ zoom }),
}));
