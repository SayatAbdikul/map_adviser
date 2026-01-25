"""
In-memory room manager for real-time location sharing.
Handles WebSocket connections, room state, and location broadcasts.
"""

import asyncio
import random
import string
import time
from dataclasses import dataclass, field
from typing import Optional
from fastapi import WebSocket


# Color palette for member markers
MEMBER_COLORS = [
    "#ef4444",  # red
    "#f97316",  # orange
    "#eab308",  # yellow
    "#22c55e",  # green
    "#06b6d4",  # cyan
    "#3b82f6",  # blue
    "#8b5cf6",  # violet
    "#ec4899",  # pink
]


def generate_room_code(length: int = 6) -> str:
    """Generate a random room code (uppercase letters + digits)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def get_member_color(index: int) -> str:
    """Get a color for a member based on their index."""
    return MEMBER_COLORS[index % len(MEMBER_COLORS)]


@dataclass
class MemberLocation:
    """Location data for a room member."""
    lat: float
    lon: float
    heading: Optional[float] = None
    accuracy: Optional[float] = None
    updated_at: float = field(default_factory=time.time)


@dataclass
class RoomMember:
    """A member in a room."""
    id: str
    nickname: str
    color: str
    websocket: WebSocket
    location: Optional[MemberLocation] = None
    joined_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    is_host: bool = False


@dataclass
class Room:
    """A collaboration room."""
    code: str
    name: str
    created_at: float = field(default_factory=time.time)
    members: dict[str, RoomMember] = field(default_factory=dict)
    
    @property
    def member_count(self) -> int:
        return len(self.members)
    
    def get_host(self) -> Optional[RoomMember]:
        for member in self.members.values():
            if member.is_host:
                return member
        return None


class RoomManager:
    """
    Manages all active rooms and their members.
    Handles WebSocket connections and location broadcasts.
    """
    
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self._member_counter = 0
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """Start background task to clean up stale rooms and members."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Periodically clean up stale members and empty rooms."""
        while True:
            await asyncio.sleep(30)  # Run every 30 seconds
            await self._cleanup_stale()
    
    async def _cleanup_stale(self):
        """Remove members who haven't sent heartbeat in 60s, and empty rooms older than 5 mins."""
        now = time.time()
        stale_timeout = 60  # seconds
        empty_room_timeout = 300  # 5 minutes before deleting empty rooms
        
        rooms_to_remove = []
        
        for room_code, room in self.rooms.items():
            members_to_remove = []
            
            for member_id, member in room.members.items():
                if now - member.last_heartbeat > stale_timeout:
                    members_to_remove.append(member_id)
            
            # Remove stale members
            for member_id in members_to_remove:
                member = room.members.pop(member_id, None)
                if member:
                    try:
                        await member.websocket.close()
                    except Exception:
                        pass
                    # Notify others about member leaving
                    await self._broadcast_member_left(room, member_id, member.nickname)
            
            # Mark empty rooms for removal (only if older than 5 minutes)
            if room.member_count == 0 and (now - room.created_at) > empty_room_timeout:
                rooms_to_remove.append(room_code)
        
        # Remove empty rooms
        for room_code in rooms_to_remove:
            del self.rooms[room_code]
    
    def create_room(self, name: str = "New Room") -> Room:
        """Create a new room with a unique code."""
        # Generate unique code
        code = generate_room_code()
        while code in self.rooms:
            code = generate_room_code()
        
        room = Room(code=code, name=name)
        self.rooms[code] = room
        return room
    
    def get_room(self, code: str) -> Optional[Room]:
        """Get a room by its code."""
        return self.rooms.get(code.upper())
    
    def delete_room(self, code: str) -> bool:
        """Delete a room."""
        if code in self.rooms:
            del self.rooms[code]
            return True
        return False
    
    async def join_room(
        self,
        room: Room,
        websocket: WebSocket,
        nickname: str,
        member_id: Optional[str] = None
    ) -> RoomMember:
        """Add a member to a room."""
        self._member_counter += 1
        
        if member_id is None:
            member_id = f"member_{self._member_counter}_{int(time.time() * 1000)}"
        
        color = get_member_color(len(room.members))
        is_host = room.member_count == 0  # First member is host
        
        member = RoomMember(
            id=member_id,
            nickname=nickname,
            color=color,
            websocket=websocket,
            is_host=is_host,
        )
        
        room.members[member_id] = member
        
        # Notify existing members about new member
        await self._broadcast_member_joined(room, member)
        
        return member
    
    async def leave_room(self, room: Room, member_id: str):
        """Remove a member from a room."""
        member = room.members.pop(member_id, None)
        if member:
            # Notify others about member leaving
            await self._broadcast_member_left(room, member_id, member.nickname)
            
            # If host left and room not empty, assign new host
            if member.is_host and room.member_count > 0:
                new_host = next(iter(room.members.values()))
                new_host.is_host = True
                await self._broadcast_host_changed(room, new_host)
    
    async def update_location(
        self,
        room: Room,
        member_id: str,
        lat: float,
        lon: float,
        heading: Optional[float] = None,
        accuracy: Optional[float] = None
    ):
        """Update a member's location and broadcast to others."""
        member = room.members.get(member_id)
        if not member:
            return
        
        member.location = MemberLocation(
            lat=lat,
            lon=lon,
            heading=heading,
            accuracy=accuracy,
        )
        member.last_heartbeat = time.time()
        
        # Broadcast location to all members
        await self._broadcast_location_update(room, member)
    
    async def heartbeat(self, room: Room, member_id: str):
        """Update member's last heartbeat time."""
        member = room.members.get(member_id)
        if member:
            member.last_heartbeat = time.time()
    
    async def _broadcast_to_room(self, room: Room, message: dict, exclude_member: Optional[str] = None):
        """Broadcast a message to all members in a room."""
        disconnected = []
        
        for member_id, member in room.members.items():
            if exclude_member and member_id == exclude_member:
                continue
            try:
                await member.websocket.send_json(message)
            except Exception:
                disconnected.append(member_id)
        
        # Clean up disconnected members
        for member_id in disconnected:
            await self.leave_room(room, member_id)
    
    async def _broadcast_member_joined(self, room: Room, new_member: RoomMember):
        """Notify all members that someone joined."""
        message = {
            "type": "member_joined",
            "member": {
                "id": new_member.id,
                "nickname": new_member.nickname,
                "color": new_member.color,
                "is_host": new_member.is_host,
            },
            "member_count": room.member_count,
        }
        await self._broadcast_to_room(room, message, exclude_member=new_member.id)
    
    async def _broadcast_member_left(self, room: Room, member_id: str, nickname: str):
        """Notify all members that someone left."""
        message = {
            "type": "member_left",
            "member_id": member_id,
            "nickname": nickname,
            "member_count": room.member_count,
        }
        await self._broadcast_to_room(room, message)
    
    async def _broadcast_host_changed(self, room: Room, new_host: RoomMember):
        """Notify all members about new host."""
        message = {
            "type": "host_changed",
            "new_host_id": new_host.id,
            "new_host_nickname": new_host.nickname,
        }
        await self._broadcast_to_room(room, message)
    
    async def _broadcast_location_update(self, room: Room, member: RoomMember):
        """Broadcast a member's location to all other members."""
        if not member.location:
            return
        
        message = {
            "type": "location_update",
            "member_id": member.id,
            "location": {
                "lat": member.location.lat,
                "lon": member.location.lon,
                "heading": member.location.heading,
                "accuracy": member.location.accuracy,
                "updated_at": member.location.updated_at,
            },
        }
        await self._broadcast_to_room(room, message, exclude_member=member.id)
    
    def get_room_state(self, room: Room) -> dict:
        """Get the full state of a room for a newly joined member."""
        members = []
        for member in room.members.values():
            member_data = {
                "id": member.id,
                "nickname": member.nickname,
                "color": member.color,
                "is_host": member.is_host,
            }
            if member.location:
                member_data["location"] = {
                    "lat": member.location.lat,
                    "lon": member.location.lon,
                    "heading": member.location.heading,
                    "accuracy": member.location.accuracy,
                    "updated_at": member.location.updated_at,
                }
            members.append(member_data)
        
        return {
            "code": room.code,
            "name": room.name,
            "created_at": room.created_at,
            "members": members,
            "member_count": room.member_count,
        }


# Global room manager instance
room_manager = RoomManager()
