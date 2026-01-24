import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { MapContainer } from '@/components/map/MapContainer';
import { ChatDrawer } from '@/components/chat/ChatDrawer';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<MapContainer />} />
          {/* Add more routes here if needed */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      <ChatDrawer />
    </BrowserRouter>
  );
};

export default App;
