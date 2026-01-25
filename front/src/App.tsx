import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { MainLayout } from '@/components/layout/MainLayout';
import { MapContainer } from '@/components/map/MapContainer';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { ChatDrawer } from '@/components/chat/ChatDrawer';
import { LandingPage } from '@/pages/LandingPage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { useAuthStore } from '@/store/useAuthStore';

const AppRoutes: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuthStore();
  const showChat = isAuthenticated && location.pathname.startsWith('/map');

  return (
    <>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<LandingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="map" element={<MapContainer />} />
            </Route>
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
