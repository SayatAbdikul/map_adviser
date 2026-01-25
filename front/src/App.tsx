import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { MapContainer } from '@/components/map/MapContainer';
import { ChatDrawer } from '@/components/chat/ChatDrawer';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';

const App: React.FC = () => {
    return (
        <BrowserRouter>
        <Routes>
        <Route path= "/login" element = {< LoginPage />} />
            < Route path = "/register" element = {< RegisterPage />} />
                < Route path = "/" element = {< MainLayout />}>
                    <Route index element = {< MapContainer />} />
{/* Add more routes here if needed */ }
<Route path="*" element = {< Navigate to = "/" replace />} />
    </Route>
    </Routes>
    < ChatDrawer />
    </BrowserRouter>
  );
};

export default App;
