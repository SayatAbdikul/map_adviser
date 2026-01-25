import { create } from 'zustand';
import type { Route, RouteResponse, RouteWaypoint } from '@/types';

interface RouteState {
  // Current route data
  routeResponse: RouteResponse | null;
  selectedRouteIndex: number;
  highlightedMovementIndex: number | null; // For segment highlighting on hover
  isLoading: boolean;
  error: string | null;

  // Actions
  setRouteResponse: (response: RouteResponse | null) => void;
  setSelectedRouteIndex: (index: number) => void;
  setHighlightedMovementIndex: (index: number | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearRoute: () => void;

  // Computed getters
  getSelectedRoute: () => Route | null;
  getRouteGeometry: () => [number, number][];
  getWaypoints: () => RouteWaypoint[];
}

export const useRouteStore = create<RouteState>((set, get) => ({
  routeResponse: null,
  selectedRouteIndex: 0,
  highlightedMovementIndex: null,
  isLoading: false,
  error: null,

  setRouteResponse: (response) => set({ routeResponse: response, error: null }),
  setSelectedRouteIndex: (index) => set({ selectedRouteIndex: index }),
  setHighlightedMovementIndex: (index) => set({ highlightedMovementIndex: index }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearRoute: () => set({ routeResponse: null, selectedRouteIndex: 0, highlightedMovementIndex: null, error: null }),

  getSelectedRoute: () => {
    const state = get();
    if (!state.routeResponse?.routes?.length) return null;
    return state.routeResponse.routes[state.selectedRouteIndex] || state.routeResponse.routes[0];
  },

  getRouteGeometry: () => {
    const route = get().getSelectedRoute();
    return route?.route_geometry || [];
  },

  getWaypoints: () => {
    const route = get().getSelectedRoute();
    return route?.waypoints || [];
  },
}));
