import { create } from 'zustand';
import type { RoomMember, MemberLocation, RoomState, WSMessage } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

interface RoomStore {
  // State
  currentRoom: RoomState | null;
  members: Map<string, RoomMember>;
  myId: string | null;
  myColor: string | null;
  myLocation: MemberLocation | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  
  // WebSocket
  ws: WebSocket | null;
  heartbeatInterval: NodeJS.Timeout | null;
  
  // Actions
  createRoom: (name?: string) => Promise<{ code: string } | null>;
  joinRoom: (code: string, nickname: string) => Promise<boolean>;
  leaveRoom: () => void;
  updateMyLocation: (location: Omit<MemberLocation, 'updated_at'>) => void;
  setError: (error: string | null) => void;
  
  // Internal
  _handleMessage: (event: MessageEvent) => void;
  _startHeartbeat: () => void;
  _stopHeartbeat: () => void;
}

export const useRoomStore = create<RoomStore>((set, get) => ({
  // Initial state
  currentRoom: null,
  members: new Map(),
  myId: null,
  myColor: null,
  myLocation: null,
  isConnected: false,
  isConnecting: false,
  error: null,
  ws: null,
  heartbeatInterval: null,
  
  // Create a new room
  createRoom: async (name = 'Trip Room') => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create room');
      }
      
      const data = await response.json();
      return { code: data.code };
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to create room' });
      return null;
    }
  },
  
  // Join an existing room via WebSocket
  joinRoom: async (code: string, nickname: string) => {
    const { ws: existingWs, leaveRoom } = get();
    
    // Close existing connection if any
    if (existingWs) {
      leaveRoom();
    }
    
    set({ isConnecting: true, error: null });
    
    return new Promise((resolve) => {
      try {
        const wsUrl = `${WS_BASE_URL}/ws/room/${code.toUpperCase()}?nickname=${encodeURIComponent(nickname)}`;
        console.log('Connecting to WebSocket:', wsUrl);
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('WebSocket connected');
          set({ ws, isConnected: true, isConnecting: false });
          get()._startHeartbeat();
        };
        
        ws.onmessage = (event) => {
          get()._handleMessage(event);
          // Resolve on first room_state message
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'room_state') {
              resolve(true);
            }
          } catch {
            // Ignore parse errors
          }
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          // Try to get more details about the error
          const wsError = error as Event;
          const errorMsg = (wsError.target as WebSocket)?.url 
            ? `Connection failed to ${(wsError.target as WebSocket).url}`
            : 'Connection error';
          set({ error: errorMsg, isConnecting: false });
          resolve(false);
        };
        
        ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          get()._stopHeartbeat();
          set({
            ws: null,
            isConnected: false,
            isConnecting: false,
            currentRoom: null,
            members: new Map(),
            myId: null,
            myColor: null,
          });
          if (event.code === 4004) {
            set({ error: 'Room not found' });
          }
          resolve(false);
        };
        
        set({ ws });
      } catch (error) {
        set({ 
          error: error instanceof Error ? error.message : 'Failed to connect',
          isConnecting: false,
        });
        resolve(false);
      }
    });
  },
  
  // Leave the current room
  leaveRoom: () => {
    const { ws, _stopHeartbeat } = get();
    _stopHeartbeat();
    
    if (ws) {
      ws.close();
    }
    
    set({
      ws: null,
      currentRoom: null,
      members: new Map(),
      myId: null,
      myColor: null,
      myLocation: null,
      isConnected: false,
      error: null,
    });
  },
  
  // Update and broadcast my location
  updateMyLocation: (location) => {
    const { ws, isConnected, myId, members } = get();
    
    const fullLocation: MemberLocation = {
      ...location,
      updated_at: Date.now() / 1000,
    };
    
    // Update myLocation state
    set({ myLocation: fullLocation });
    
    // Also update our entry in the members map so UI stays consistent
    if (myId) {
      const me = members.get(myId);
      if (me) {
        const newMembers = new Map(members);
        newMembers.set(myId, { ...me, location: fullLocation });
        set({ members: newMembers });
      }
    }
    
    // Broadcast to server
    if (ws && isConnected) {
      ws.send(JSON.stringify({
        type: 'location',
        lat: location.lat,
        lon: location.lon,
        heading: location.heading,
        accuracy: location.accuracy,
      }));
    }
  },
  
  setError: (error) => set({ error }),
  
  // Handle incoming WebSocket messages
  _handleMessage: (event) => {
    try {
      const data: WSMessage = JSON.parse(event.data);
      
      switch (data.type) {
        case 'room_state': {
          const roomState = data as unknown as RoomState & { type: string };
          const membersMap = new Map<string, RoomMember>();
          roomState.members.forEach((m: RoomMember) => membersMap.set(m.id, m));
          
          set({
            currentRoom: roomState,
            members: membersMap,
            myId: roomState.your_id,
            myColor: roomState.your_color,
          });
          break;
        }
        
        case 'member_joined': {
          const payload = data as unknown as { member: RoomMember; member_count: number };
          const { member, member_count } = payload;
          set((state) => {
            const newMembers = new Map(state.members);
            newMembers.set(member.id, member);
            return {
              members: newMembers,
              currentRoom: state.currentRoom
                ? { ...state.currentRoom, member_count }
                : null,
            };
          });
          break;
        }
        
        case 'member_left': {
          const payload = data as unknown as { member_id: string; member_count: number };
          const { member_id, member_count } = payload;
          set((state) => {
            const newMembers = new Map(state.members);
            newMembers.delete(member_id);
            return {
              members: newMembers,
              currentRoom: state.currentRoom
                ? { ...state.currentRoom, member_count }
                : null,
            };
          });
          break;
        }
        
        case 'location_update': {
          const payload = data as unknown as { member_id: string; location: MemberLocation };
          const { member_id, location } = payload;
          set((state) => {
            const newMembers = new Map(state.members);
            const member = newMembers.get(member_id);
            if (member) {
              newMembers.set(member_id, { ...member, location });
            }
            return { members: newMembers };
          });
          break;
        }
        
        case 'host_changed': {
          const payload = data as unknown as { new_host_id: string };
          const { new_host_id } = payload;
          set((state) => {
            const newMembers = new Map(state.members);
            newMembers.forEach((member, id) => {
              newMembers.set(id, { ...member, is_host: id === new_host_id });
            });
            return { members: newMembers };
          });
          break;
        }
        
        case 'error': {
          const payload = data as unknown as { message: string };
          const { message } = payload;
          set({ error: message });
          break;
        }
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  },
  
  // Start heartbeat to keep connection alive
  _startHeartbeat: () => {
    const { _stopHeartbeat } = get();
    _stopHeartbeat();
    
    const interval = setInterval(() => {
      const { ws, isConnected } = get();
      if (ws && isConnected) {
        ws.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 25000); // Send heartbeat every 25 seconds
    
    set({ heartbeatInterval: interval });
  },
  
  // Stop heartbeat
  _stopHeartbeat: () => {
    const { heartbeatInterval } = get();
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
      set({ heartbeatInterval: null });
    }
  },
}));
