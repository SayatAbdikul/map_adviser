import React, { useState } from 'react';
import { twMerge } from 'tailwind-merge';
import { useAppStore } from '@/store/useAppStore';
import { X, Search, Navigation, MessageSquare, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { useChatStore } from '@/store/useChatStore';
import { SearchBar } from '@/components/search/SearchBar';
import { SearchResults } from '@/components/search/SearchResults';
import type { Place } from '@/services/mapService';
import { useMapStore } from '@/store/useMapStore';

export const Sidebar: React.FC = () => {
  const { isSidebarOpen, toggleSidebar, sidebarView, setSidebarView } = useAppStore();
  const { toggleChat } = useChatStore();
  const { setCenter, setZoom } = useMapStore();
  const [searchResults, setSearchResults] = useState<Place[]>([]);

  const handlePlaceSelect = (place: Place) => {
    setCenter(place.coordinates);
    setZoom(16);
    // On mobile we might want to close sidebar
    if (window.innerWidth < 768) {
      toggleSidebar();
    }
  };

  const renderContent = () => {
    switch (sidebarView) {
      case 'search':
        return (
          <div className="p-4 flex flex-col h-full">
             <div className="flex items-center mb-4">
                <Button variant="ghost" size="sm" onClick={() => setSidebarView('menu')} className="mr-2 p-1 h-8 w-8">
                  <ArrowLeft size={18} />
                </Button>
                <h2 className="font-semibold text-lg">Search</h2>
             </div>
             <SearchBar 
                onResults={setSearchResults} 
                onClear={() => setSearchResults([])} 
             />
             <SearchResults results={searchResults} onSelect={handlePlaceSelect} />
          </div>
        );
      case 'routes':
        return (
          <div className="p-4 flex flex-col h-full">
            <div className="flex items-center mb-4">
                <Button variant="ghost" size="sm" onClick={() => setSidebarView('menu')} className="mr-2 p-1 h-8 w-8">
                  <ArrowLeft size={18} />
                </Button>
                <h2 className="font-semibold text-lg">Routes</h2>
             </div>
             <div className="app-surface-2 p-4 rounded-lg text-center app-muted text-sm">
                Route planning implementation pending...
             </div>
          </div>
        );
      default:
        return (
          <nav className="flex-1 overflow-y-auto p-4 space-y-2">
            <div className="text-xs font-semibold app-muted uppercase tracking-wider mb-2">
              Menu
            </div>
            
            <Button 
              variant="ghost" 
              className="w-full justify-start" 
              leftIcon={<Search size={18} />}
              onClick={() => setSidebarView('search')}
            >
              Search Places
            </Button>
            
            <Button 
              variant="ghost" 
              className="w-full justify-start" 
              leftIcon={<Navigation size={18} />}
              onClick={() => setSidebarView('routes')}
            >
              Routes
            </Button>

            <Button 
              variant="ghost" 
              className="w-full justify-start" 
              leftIcon={<MessageSquare size={18} />}
              onClick={toggleChat}
            >
              Chat Assistant
            </Button>
          </nav>
        );
    }
  };

  return (
    <>
      {/* Overlay for mobile */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm md:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={twMerge(
          'fixed inset-y-0 left-0 z-50 w-80 app-surface app-shadow transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0',
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full border-r app-border">
          {/* Header */}
          <div className="p-4 border-b app-border flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-[color:var(--app-accent)] rounded-lg flex items-center justify-center text-[color:var(--app-accent-contrast)] font-bold">
                MA
              </div>
              <span className="font-bold app-text text-lg">Map Adviser</span>
            </div>
            <button 
              onClick={toggleSidebar}
              className="md:hidden text-[color:var(--app-muted)] hover:text-[color:var(--app-text)]"
            >
              <X size={20} />
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
             {renderContent()}
          </div>

          {/* Footer */}
          <div className="p-4 border-t app-border app-surface-2">
            <div className="text-xs text-center app-muted">
              © 2024 Map Adviser
              <br />
              Powered by 2GIS
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
