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

export interface Place {
    id: string;
    name: string;
    address: string;
    lat: number;
    lon: number;
    type?: string;
}

export interface RouteResponse {
    places: Place[];
    route_url: string;
    total_distance?: number;  // in meters
    total_duration?: number;  // in seconds
    gemini_explanation: string;
}

export interface RouteRequest {
    query: string;
    mode?: 'driving' | 'walking' | 'public_transport';
}

export interface ApiError {
    detail: string | { error: string; raw_response?: string };
}

// ==================== Room Sync Types ====================

export interface MemberLocation {
    lat: number;
    lon: number;
    heading?: number | null;
    accuracy?: number | null;
    updated_at: number;
}

export interface RoomMember {
    id: string;
    nickname: string;
    color: string;
    is_host: boolean;
    location?: MemberLocation;
}

export interface Room {
    code: string;
    name: string;
    created_at: number;
    members: RoomMember[];
    member_count: number;
}

export interface RoomState extends Room {
    your_id: string;
    your_color: string;
}

// WebSocket message types
export type WSMessageType =
    | 'room_state'
    | 'member_joined'
    | 'member_left'
    | 'location_update'
    | 'host_changed'
    | 'heartbeat_ack'
    | 'error';

export interface WSMessage {
    type: WSMessageType;
    [key: string]: unknown;
}

export interface WSLocationUpdateMessage extends WSMessage {
    type: 'location_update';
    member_id: string;
    location: MemberLocation;
}

export interface WSMemberJoinedMessage extends WSMessage {
    type: 'member_joined';
    member: RoomMember;
    member_count: number;
}

export interface WSMemberLeftMessage extends WSMessage {
    type: 'member_left';
    member_id: string;
    nickname: string;
    member_count: number;
}

export interface WSRoomStateMessage extends WSMessage, RoomState {
    type: 'room_state';
}
