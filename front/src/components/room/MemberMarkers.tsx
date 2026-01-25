import { useEffect, useRef, useState } from 'react';
import { load } from '@2gis/mapgl';
import { Map as MapGL, HtmlMarker } from '@2gis/mapgl/types';
import { useRoomStore } from '@/store/useRoomStore';

interface MemberMarkersProps {
  map: MapGL | null;
}

// Create a custom marker element for a member
const createMemberMarkerElement = (
  nickname: string,
  color: string,
  isMe: boolean,
  heading: number | null | undefined
): HTMLElement => {
  const container = document.createElement('div');
  container.className = 'member-marker';
  container.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    transform: translate(-50%, -100%);
    pointer-events: auto;
  `;

  // Name label
  const label = document.createElement('div');
  label.textContent = nickname + (isMe ? ' (you)' : '');
  label.style.cssText = `
    background: ${color};
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    margin-bottom: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  `;

  // Pin marker
  const pin = document.createElement('div');
  pin.style.cssText = `
    width: 24px;
    height: 24px;
    background: ${color};
    border: 3px solid white;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  `;

  // Add direction indicator if heading is available
  if (heading !== null && heading !== undefined) {
    const arrow = document.createElement('div');
    arrow.style.cssText = `
      width: 0;
      height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 10px solid ${color};
      position: absolute;
      top: -14px;
      left: 50%;
      transform: translateX(-50%) rotate(${heading}deg);
      transform-origin: center bottom;
    `;
    container.style.position = 'relative';
    container.appendChild(arrow);
  }

  container.appendChild(label);
  container.appendChild(pin);

  return container;
};

export const MemberMarkers: React.FC<MemberMarkersProps> = ({ map }) => {
  const { members, myId, myLocation } = useRoomStore();
  const markersRef = useRef<Map<string, HtmlMarker>>(new Map());
  const [mapglAPI, setMapglAPI] = useState<Awaited<ReturnType<typeof load>> | null>(null);
  const hasInitiallyPanned = useRef(false);

  // Load mapgl API
  useEffect(() => {
    load().then(api => setMapglAPI(api));
  }, []);

  // Auto-pan to my location when first received
  useEffect(() => {
    if (!map || !myLocation || hasInitiallyPanned.current) return;
    
    map.setCenter([myLocation.lon, myLocation.lat]);
    map.setZoom(15);
    hasInitiallyPanned.current = true;
    console.log('Panned to my location:', myLocation.lat, myLocation.lon);
  }, [map, myLocation]);

  // Reset the initial pan flag when leaving room
  useEffect(() => {
    if (!myId) {
      hasInitiallyPanned.current = false;
    }
  }, [myId]);

  useEffect(() => {
    if (!map || !mapglAPI) return;

    const currentMarkers = markersRef.current;
    
    // Build members with location, including self with myLocation
    const membersWithLocation = Array.from(members.values())
      .map(member => {
        // For self, use myLocation which is more up-to-date
        if (member.id === myId && myLocation) {
          return { ...member, location: myLocation };
        }
        return member;
      })
      .filter(m => m.location);
    
    console.log('MemberMarkers update:', { 
      memberCount: members.size, 
      withLocation: membersWithLocation.length,
      myId,
      myLocation 
    });

    // Remove markers for members who left or lost location
    currentMarkers.forEach((marker, memberId) => {
      const memberStillExists = membersWithLocation.find(m => m.id === memberId);
      if (!memberStillExists) {
        marker.destroy();
        currentMarkers.delete(memberId);
      }
    });

    // Update or create markers for members with locations
    membersWithLocation.forEach((member) => {
      if (!member.location) return;

      const existingMarker = currentMarkers.get(member.id);
      const isMe = member.id === myId;

      if (existingMarker) {
        // Update position
        existingMarker.setCoordinates([member.location.lon, member.location.lat]);
      } else {
        // Create new marker
        const element = createMemberMarkerElement(
          member.nickname,
          member.color,
          isMe,
          member.location.heading
        );

        const marker = new mapglAPI.HtmlMarker(map, {
          coordinates: [member.location.lon, member.location.lat],
          html: element,
          anchor: [0.5, 1],
        });

        currentMarkers.set(member.id, marker);
        console.log('Created marker for', member.nickname, 'at', member.location.lat, member.location.lon);
      }
    });
  }, [map, mapglAPI, members, myId, myLocation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      markersRef.current.forEach((marker) => {
        marker.destroy();
      });
      markersRef.current.clear();
    };
  }, []);

  return null; // This component doesn't render anything directly
};
