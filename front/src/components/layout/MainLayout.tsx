import React from 'react';
import { Outlet } from 'react-router-dom';
import { useAppStore } from '@/store/useAppStore';
import { Sidebar } from './Sidebar';
import { Menu } from 'lucide-react';
import { Button } from '@/components/common/Button';

export const MainLayout: React.FC = () => {
  const { toggleSidebar } = useAppStore();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50">
      {/* Mobile Header */}
      <div className="absolute top-4 left-4 z-50 md:hidden">
        <Button 
          variant="secondary" 
          size="sm" 
          onClick={toggleSidebar}
          className="shadow-md bg-white"
        >
          <Menu size={20} />
        </Button>
      </div>

      <Sidebar />
      
      <main className="flex-1 relative h-full w-full">
        <Outlet />
      </main>
    </div>
  );
};
