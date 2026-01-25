import React from 'react';
import { Outlet } from 'react-router-dom';
import { ThemePanel } from '@/components/theme/ThemePanel';

export const MainLayout: React.FC = () => {
  return (
    <div className="relative flex h-screen w-screen overflow-hidden app-canvas text-[color:var(--app-text)]">
      <div className="absolute inset-0 theme-backdrop" />
      <main className="relative flex-1 h-full w-full">
        <Outlet />
      </main>
      <ThemePanel />
    </div>
  );
};
