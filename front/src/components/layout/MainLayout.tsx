import React from 'react';
import { Outlet } from 'react-router-dom';

export const MainLayout: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50">
      <main className="flex-1 relative h-full w-full">
        <Outlet />
      </main>
    </div>
  );
};
