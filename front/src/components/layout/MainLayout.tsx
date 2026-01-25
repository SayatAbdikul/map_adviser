import React from 'react';
import { Outlet } from 'react-router-dom';

export const MainLayout: React.FC = () => {
  return (
    <div className="relative flex h-screen w-screen overflow-hidden">
      <main className="relative flex-1 h-full w-full">
        <Outlet />
      </main>
    </div>
  );
};
