import { useAuthStore } from '@/store/useAuthStore';

export const authService = {
    login: async (email: string, password: string) => {
        const { login } = useAuthStore.getState();
        return login(email, password);
    },

    register: async (email: string, password: string, name: string) => {
        const { register } = useAuthStore.getState();
        return register(email, password, name);
    },

    logout: () => {
        const { logout } = useAuthStore.getState();
        logout();
    },

    getAuthHeaders: () => {
        const token = localStorage.getItem('auth_token');
        if (!token) return {};
        return { Authorization: `Bearer ${token}` };
    },

    isAuthenticated: () => {
        return !!localStorage.getItem('auth_token');
    },

    getToken: () => {
        return localStorage.getItem('auth_token');
    },
};
