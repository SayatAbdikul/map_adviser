import React, { useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/store/useAuthStore';
import { Loader } from '@/components/common/Loader';

export const ProtectedRoute: React.FC = () => {
    const { isAuthenticated, isLoading, verifyToken } = useAuthStore();

    useEffect(() => {
        // Verify token on component mount
        verifyToken();
    }, []);

    if (isLoading) {
        return (
            <div className= "min-h-screen flex items-center justify-center bg-gray-100" >
            <Loader className="w-8 h-8" />
                </div>
        );
    }

if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
}

return <Outlet />;
};
