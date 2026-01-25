// Route API types

export interface RouteWaypoint {
  order: number;
  type: 'start' | 'stop' | 'end';
  name: string;
  address: string;
  location: {
    lat: number;
    lon: number;
  };
  category: string | null;
  // Computed helpers for frontend
  lat?: number;
  lon?: number;
}

export interface RouteDirection {
  instruction: string;
  type: string;
  street_name: string;
  distance_meters: number;
  duration_seconds: number;
}

export interface RouteSegmentInfo {
  from_waypoint: number;
  to_waypoint: number;
  distance_meters: number;
  duration_seconds: number;
  // Added for geometry rendering
  geometry?: [number, number][];
  color?: string;
}

export interface Route {
  route_id: number;
  title: string;
  total_distance_meters: number | null;
  total_duration_minutes: number | null;
  waypoints: RouteWaypoint[];
  route_geometry?: [number, number][]; // [lon, lat][]
  directions?: RouteDirection[];
  segments?: RouteSegmentInfo[];
  // Public transport specific
  transport_chain?: string;
  transfer_count?: number;
  walking_duration_minutes?: number;
  // Time-based planning
  recommended_departure_time?: string; // "HH:MM"
  estimated_arrival_time?: string; // "HH:MM"
}

export interface RequestSummary {
  origin_address: string;
  intent: string;
  transport_mode?: string;
  optimization_choice?: string;
  // Time-based planning
  arrival_time?: string; // Desired arrival time "HH:MM"
  departure_time?: string; // Recommended departure time "HH:MM"
}

export interface RouteResponse {
  request_summary: RequestSummary;
  routes: Route[];
  // Helper computed properties for frontend
  waypoints?: Array<{ lat: number; lon: number; name: string; address: string; type: string }>;
}

export interface RouteRequest {
  query: string;
  mode?: 'driving' | 'walking' | 'public_transport';
}

export interface ApiError {
  detail: string | { error: string; raw_response?: string };
}
