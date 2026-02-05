import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { MainLayout } from '@/components/layout/MainLayout';
import { MapContainer } from '@/components/map/MapContainer';
import { ChatDrawer } from '@/components/chat/ChatDrawer';

const AppRoutes: React.FC = () => {
  const location = useLocation();
  const showChat =
    location.pathname === '/' || location.pathname.startsWith('/map');

  return (
    <>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route element={<MainLayout />}>
            <Route index element={<MapContainer />} />
            <Route path="map" element={<MapContainer />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      {showChat && <ChatDrawer />}
    </>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
};

export default App;
