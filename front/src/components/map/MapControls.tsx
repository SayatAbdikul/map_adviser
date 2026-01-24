import React from 'react';
import { Plus, Minus, Navigation } from 'lucide-react';
import { useMapStore } from '@/store/useMapStore';
import { Button } from '@/components/common/Button';

export const MapControls: React.FC = () => {
  const { mapInstance } = useMapStore();

  const handleZoomIn = () => {
    if (mapInstance) {
      mapInstance.setZoom(mapInstance.getZoom() + 1);
    }
  };

  const handleZoomOut = () => {
    if (mapInstance) {
      mapInstance.setZoom(mapInstance.getZoom() - 1);
    }
  };

  const handleLocateMe = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition((position) => {
        if (mapInstance) {
          mapInstance.setCenter([position.coords.longitude, position.coords.latitude]);
          mapInstance.setZoom(15);
        }
      });
    }
  };

  return (
    <div className="absolute bottom-8 right-4 flex flex-col space-y-2 z-10">
      <div className="flex flex-col bg-white rounded-lg shadow-lg overflow-hidden">
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={handleZoomIn}
          className="rounded-none border-b border-gray-100 h-10 w-10 p-0"
        >
          <Plus size={20} />
        </Button>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={handleZoomOut}
          className="rounded-none h-10 w-10 p-0"
        >
          <Minus size={20} />
        </Button>
      </div>

      <Button 
        variant="primary" 
        onClick={handleLocateMe}
        className="rounded-full h-12 w-12 p-0 shadow-lg"
      >
        <Navigation size={20} />
      </Button>
    </div>
  );
};
