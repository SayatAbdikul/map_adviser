import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { buildApiUrl } from '@/constants';

export interface User {
    id: number;
    email: string;
    name: string;
    avatar_url?: string;
}

interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    error: string | null;
    isAuthenticated: boolean;
    // Actions
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, name: string) => Promise<void>;
    verifyToken: () => Promise<void>;
    logout: () => void;
    setError: (error: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: localStorage.getItem('auth_token'),
            isLoading: false,
            error: null,
            isAuthenticated: !!localStorage.getItem('auth_token'),

            login: async (email: string, password: string) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await fetch(buildApiUrl('/auth/login'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password }),
                    });

                    if (!response.ok) {
                        let errorMessage = 'Login failed';
                        try {
                            const data = await response.json();
                            errorMessage = data.detail || `Login failed: ${response.status}`;
                        } catch {
                            errorMessage = `Login failed: ${response.status} ${response.statusText}`;
                        }
                        throw new Error(errorMessage);
                    }

                    const data = await response.json();

                    localStorage.setItem('auth_token', data.access_token);

                    set({
                        user: {
                            id: data.user_id,
                            email: data.email,
                            name: data.name,
                        },
                        token: data.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (error) {
                    let message = 'Login failed';
                    if (error instanceof TypeError && error.message === 'Failed to fetch') {
                        message = 'Unable to connect to server. Please check if the server is running.';
                    } else if (error instanceof Error) {
                        message = error.message;
                    }
                    set({ error: message, isLoading: false });
                    throw error;
                }
            },

            register: async (email: string, password: string, name: string) => {
                set({ isLoading: true, error: null });
                try {
                    // Split name into first_name and last_name for backend
                    const nameParts = name.trim().split(' ');
                    const first_name = nameParts[0] || name;
                    const last_name = nameParts.slice(1).join(' ') || '';
                    const login = email.split('@')[0]; // Use email prefix as login

                    const response = await fetch(buildApiUrl('/auth/register'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password, login, first_name, last_name }),
                    });

                    if (!response.ok) {
                        let errorMessage = 'Registration failed';
                        try {
                            const data = await response.json();
                            // Handle FastAPI validation errors (array of objects with msg field)
                            if (Array.isArray(data.detail)) {
                                errorMessage = data.detail.map((err: any) => err.msg || String(err)).join(', ');
                            } else {
                                errorMessage = data.detail || `Registration failed: ${response.status}`;
                            }
                        } catch {
                            errorMessage = `Registration failed: ${response.status} ${response.statusText}`;
                        }
                        throw new Error(errorMessage);
                    }

                    const data = await response.json();

                    localStorage.setItem('auth_token', data.access_token);

                    set({
                        user: {
                            id: data.user_id,
                            email: data.email,
                            name: data.name,
                        },
                        token: data.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (error) {
                    let message = 'Registration failed';
                    if (error instanceof TypeError && error.message === 'Failed to fetch') {
                        message = 'Unable to connect to server. Please check if the server is running.';
                    } else if (error instanceof Error) {
                        message = error.message;
                    }
                    set({ error: message, isLoading: false });
                    throw error;
                }
            },

            verifyToken: async () => {
                const token = get().token || localStorage.getItem('auth_token');
                if (!token) {
                    set({ isAuthenticated: false, user: null });
                    return;
                }

                set({ isLoading: true });
                try {
                    const response = await fetch(buildApiUrl('/auth/me'), {
                        headers: { 'Authorization': `Bearer ${token}` },
                    });

                    if (!response.ok) {
                        throw new Error('Token verification failed');
                    }

                    const user = await response.json();
                    set({
                        user,
                        token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (error) {
                    localStorage.removeItem('auth_token');
                    set({
                        user: null,
                        token: null,
                        isAuthenticated: false,
                        isLoading: false,
                    });
                }
            },

            logout: () => {
                localStorage.removeItem('auth_token');
                set({
                    user: null,
                    token: null,
                    isAuthenticated: false,
                    error: null,
                });
            },

            setError: (error: string | null) => {
                set({ error });
            },
        }),
        {
            name: 'auth-store',
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);
