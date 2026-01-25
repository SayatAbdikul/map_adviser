import React from 'react';
import { Outlet } from 'react-router-dom';
import { ThemePanel } from '@/components/theme/ThemePanel';

export const AppShell: React.FC = () => {
  return (
    <div className="relative min-h-screen w-full overflow-x-hidden app-canvas text-[color:var(--app-text)]">
      <div className="pointer-events-none absolute inset-0 theme-backdrop" />
      <div className="relative min-h-screen">
        <Outlet />
      </div>
      <ThemePanel />
    </div>
  );
};
