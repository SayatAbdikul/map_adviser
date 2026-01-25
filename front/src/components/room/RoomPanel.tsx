import React, { useState, useEffect, useCallback } from 'react';
import { Users, Share2, Copy, Check, MapPin, X, LogOut, UserPlus, MousePointer, Navigation } from 'lucide-react';
import { useRoomStore } from '@/store/useRoomStore';

export const RoomPanel: React.FC = () => {
  const {
    currentRoom,
    members,
    myId,
    myLocation,
    isConnected,
    isConnecting,
    error,
    isManualLocationMode,
    createRoom,
    joinRoom,
    leaveRoom,
    updateMyLocation,
    setError,
    setManualLocationMode,
  } = useRoomStore();

  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [nickname, setNickname] = useState('');
  const [copied, setCopied] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [watchId, setWatchId] = useState<number | null>(null);

  // Start/stop location tracking
  const toggleTracking = useCallback(() => {
    if (isTracking && watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
      setIsTracking(false);
    } else if ('geolocation' in navigator) {
      const id = navigator.geolocation.watchPosition(
        (position) => {
          updateMyLocation({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            heading: position.coords.heading,
            accuracy: position.coords.accuracy,
          });
        },
        (error) => {
          console.error('Geolocation error:', error);
          setError('Failed to get location: ' + error.message);
        },
        {
          enableHighAccuracy: true,
          maximumAge: 5000,
          timeout: 10000,
        }
      );
      setWatchId(id);
      setIsTracking(true);
    } else {
      setError('Geolocation is not supported');
    }
  }, [isTracking, watchId, updateMyLocation, setError]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [watchId]);

  // Reset manual mode when leaving room
  useEffect(() => {
    if (!isConnected) {
      setManualLocationMode(false);
    }
  }, [isConnected, setManualLocationMode]);

  const handleCreateRoom = async () => {
    const defaultNickname = nickname.trim() || `User_${Math.floor(Math.random() * 1000)}`;
    const result = await createRoom('Trip Room');
    if (result) {
      await joinRoom(result.code, defaultNickname);
      setShowShareModal(true);
    }
  };

  const handleJoinRoom = async () => {
    if (!joinCode.trim()) return;
    const defaultNickname = nickname.trim() || `User_${Math.floor(Math.random() * 1000)}`;
    const success = await joinRoom(joinCode.trim(), defaultNickname);
    if (success) {
      setShowJoinModal(false);
      setJoinCode('');
    }
  };

  const handleLeaveRoom = () => {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
      setIsTracking(false);
    }
    leaveRoom();
  };

  const copyRoomCode = () => {
    if (currentRoom) {
      navigator.clipboard.writeText(currentRoom.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const membersArray = Array.from(members.values());

  // Not in a room - show create/join buttons
  if (!currentRoom) {
    return (
      <>
        <div className="absolute top-4 right-4 z-20 bg-white rounded-lg shadow-lg p-3">
          <div className="flex flex-col gap-2">
            <div className="text-sm font-medium text-gray-700 mb-1">Location Sharing</div>
            
            <input
              type="text"
              placeholder="Your nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            
            <button
              onClick={handleCreateRoom}
              disabled={isConnecting}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm font-medium"
            >
              <Share2 size={16} />
              Create Room
            </button>
            
            <button
              onClick={() => setShowJoinModal(true)}
              disabled={isConnecting}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 text-sm font-medium"
            >
              <UserPlus size={16} />
              Join Room
            </button>
            
            {error && (
              <div className="text-xs text-red-500 mt-1">{error}</div>
            )}
          </div>
        </div>

        {/* Join Room Modal */}
        {showJoinModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl p-6 w-80 shadow-xl">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Join Room</h3>
                <button onClick={() => setShowJoinModal(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={20} />
                </button>
              </div>
              
              <input
                type="text"
                placeholder="Room Code"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                className="w-full px-4 py-2 text-lg font-mono tracking-wider border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3 uppercase text-center"
                maxLength={6}
              />
              
              <button
                onClick={handleJoinRoom}
                disabled={!joinCode.trim() || isConnecting}
                className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 font-medium"
              >
                {isConnecting ? 'Joining...' : 'Join'}
              </button>
              
              {error && (
                <div className="text-sm text-red-500 mt-2 text-center">{error}</div>
              )}
            </div>
          </div>
        )}
      </>
    );
  }

  // In a room - show room info and members
  return (
    <>
      <div className="absolute top-4 right-4 z-20 bg-white rounded-lg shadow-lg p-3 min-w-[200px]">
        {/* Room header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            <span className="font-medium text-sm">{currentRoom.name}</span>
          </div>
          <button
            onClick={handleLeaveRoom}
            className="text-gray-400 hover:text-red-500 transition-colors"
            title="Leave room"
          >
            <LogOut size={16} />
          </button>
        </div>
        
        {/* Room code */}
        <div className="flex items-center gap-2 mb-3 p-2 bg-gray-50 rounded-lg">
          <span className="text-xs text-gray-500">Code:</span>
          <span className="font-mono font-bold tracking-wider text-blue-600">{currentRoom.code}</span>
          <button
            onClick={copyRoomCode}
            className="ml-auto text-gray-400 hover:text-blue-500"
            title="Copy code"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          </button>
        </div>
        
        {/* Members list */}
        <div className="space-y-2">
          <div className="text-xs text-gray-500 font-medium">
            Members ({membersArray.length})
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {membersArray.map((member) => (
              <div
                key={member.id}
                className="flex items-center gap-2 p-1.5 rounded-md hover:bg-gray-50"
              >
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: member.color }}
                />
                <span className="text-sm truncate flex-1">
                  {member.nickname}
                  {member.id === myId && ' (you)'}
                </span>
                {member.location && (
                  <MapPin size={12} className="text-green-500 flex-shrink-0" />
                )}
                {member.is_host && (
                  <span className="text-[10px] bg-yellow-100 text-yellow-700 px-1 rounded">Host</span>
                )}
              </div>
            ))}
          </div>
        </div>
        
        {/* Location tracking status */}
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
          <div className="text-xs text-gray-500 font-medium mb-1">Set Your Location</div>
          
          {/* GPS Tracking button */}
          <button
            onClick={() => {
              if (isManualLocationMode) {
                setManualLocationMode(false);
              }
              toggleTracking();
            }}
            className={`w-full py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1 ${
              isTracking && !isManualLocationMode
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Navigation size={12} />
            {isTracking && !isManualLocationMode ? 'GPS Active' : 'Use GPS'}
          </button>
          
          {/* Manual location button */}
          <button
            onClick={() => {
              if (isTracking && watchId !== null) {
                navigator.geolocation.clearWatch(watchId);
                setWatchId(null);
                setIsTracking(false);
              }
              setManualLocationMode(!isManualLocationMode);
            }}
            className={`w-full py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1 ${
              isManualLocationMode
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 ring-2 ring-blue-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <MousePointer size={12} />
            {isManualLocationMode ? 'Click map to set location...' : 'Set on Map'}
          </button>
          
          {myLocation && (
            <div className="text-[10px] text-gray-400 mt-1 text-center">
              {myLocation.lat.toFixed(5)}, {myLocation.lon.toFixed(5)}
            </div>
          )}
        </div>
      </div>

      {/* Share Modal */}
      {showShareModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl p-6 w-80 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Room Created!</h3>
              <button onClick={() => setShowShareModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              Share this code with others to let them join:
            </p>
            
            <div className="flex items-center justify-center gap-3 p-4 bg-gray-50 rounded-lg mb-4">
              <span className="text-2xl font-mono font-bold tracking-widest text-blue-600">
                {currentRoom.code}
              </span>
              <button
                onClick={copyRoomCode}
                className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg"
              >
                {copied ? <Check size={20} className="text-green-500" /> : <Copy size={20} />}
              </button>
            </div>
            
            <button
              onClick={() => setShowShareModal(false)}
              className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </>
  );
};
