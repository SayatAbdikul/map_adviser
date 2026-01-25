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
    street_name?: string;
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

// Public transport movement (segment) details
export interface PublicTransportMovement {
  type: 'walkway' | 'passage' | 'transfer';
  subtype?: string;
  transport_type?: string; // 'metro', 'bus', 'tram', 'walk', etc.
  duration_seconds: number;
  distance_meters: number;
  // Stop information
  from_name?: string;
  from_stop?: string;
  to_stop?: string;
  stops_count?: number;
  // Transport details
  line_name?: string;
  line_color?: string;
  route_name?: string;
  route_color?: string;
  direction?: string;
  station_count?: string;
  // Geometry for map display
  geometry?: [number, number][];
}

// Schedule information for public transport
export interface PublicTransportSchedule {
  type?: string;
  period_minutes?: number;
  departure_time?: string;
  start_time_utc?: number;
}

export interface Route {
  route_id: number;
  title?: string;
  total_distance_meters?: number | null;
  total_duration_minutes?: number | null;
  waypoints: RouteWaypoint[];
  route_geometry?: [number, number][]; // [lon, lat][]
  directions?: Direction[];
  segments?: RouteSegmentInfo[];
  // Public transport specific
  transport_chain?: string;
  transfer_count?: number;
  walking_duration_minutes?: number;
  movements?: PublicTransportMovement[]; // Detailed movement segments
  schedule?: PublicTransportSchedule; // Schedule information
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

// Legacy routing service response format
export interface LegacyRouteResponse {
    places: Place[];
    route_url: string;
    total_distance?: number;  // in meters
    total_duration?: number;  // in seconds
    gemini_explanation: string;
}

// New core agent response format
export interface CoreAgentResponse {
    routes: CoreRoute[];
    request_summary?: {
        optimization_choice?: string;
        transport_mode?: string;
    };
}

export interface CoreRoute {
    route_id: number;
    title?: string;
    total_distance_meters?: number;
    total_duration_minutes?: number;
    recommended_departure_time?: string;
    estimated_arrival_time?: string;
    transport_chain?: string;
    transfer_count?: number;
    walking_duration_minutes?: number;
    movements?: Movement[];
    waypoints: RouteWaypoint[];
    route_geometry?: [number, number][];
    directions?: Direction[];
    segments?: Segment[];
    schedule?: PublicTransportSchedule; // Add schedule support
}

export interface Movement {
    type: 'walkway' | 'passage' | 'transfer';
    transport_type: 'walk' | 'metro' | 'bus' | 'tram' | 'trolleybus';
    duration_seconds: number;
    distance_meters: number;
    from_name: string;
    from_stop?: string;
    to_stop?: string;
    line_name?: string;
    line_color?: string;
    route_name?: string;
    route_color?: string;
    geometry?: [number, number][];
}

export interface Direction {
    instruction: string;
    type: string;
    street_name?: string;
    distance_meters?: number;
    duration_seconds?: number;
}

export interface Segment {
    from_waypoint: number;
    to_waypoint: number;
    distance_meters: number;
    duration_seconds: number;
}

// Union type to support both formats
export type RouteResponse = LegacyRouteResponse | CoreAgentResponse;

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
    chat_messages?: ChatMessage[];
}

// ==================== Room Chat Types ====================

export interface ChatMessage {
    id: string;
    sender_id: string;
    sender_nickname: string;
    content: string;
    timestamp: number;
    is_agent_response: boolean;
    route_data?: ChatRouteData | null;
}

export interface MeetingPlaceDestination {
    name: string;
    address: string;
    coordinates: [number, number]; // [lon, lat]
}

export interface MemberTravelTime {
    member_id: string;
    member_nickname: string;
    duration_seconds: number | null;
    duration_minutes: number;
    distance_meters: number;
    error?: string;
}

export interface MemberRoute {
    member_id: string;
    member_nickname: string;
    distance_meters: number;
    duration_seconds: number;
    duration_minutes: number;
    geometry: [number, number][]; // [lon, lat][]
}

export interface ChatRouteData {
    type: 'meeting_place' | 'routes_to_destination';
    destination: MeetingPlaceDestination;
    centroid?: { longitude: number; latitude: number };
    member_travel_times?: MemberTravelTime[];
    member_routes?: MemberRoute[];
}

export interface Place {
    id: string;
    name: string;
    address: string;
    lat: number;
    lon: number;
    type?: string;
}


export type WSMessageType =
    | 'room_state'
    | 'member_joined'
    | 'member_left'
    | 'location_update'
    | 'host_changed'
    | 'heartbeat_ack'
    | 'room_chat_message'
    | 'agent_typing'
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

export interface WSChatMessageReceived extends WSMessage {
    type: 'room_chat_message';
    message: ChatMessage;
}

export interface WSAgentTyping extends WSMessage {
    type: 'agent_typing';
    is_typing: boolean;
}

// Type guards for route responses
export function isCoreAgentResponse(response: RouteResponse): response is CoreAgentResponse {
    return 'routes' in response && Array.isArray(response.routes);
}

export function isLegacyResponse(response: RouteResponse): response is LegacyRouteResponse {
    return 'places' in response && Array.isArray(response.places);
}
