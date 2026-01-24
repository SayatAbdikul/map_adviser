import { create } from 'zustand';

interface AppState {
  isSidebarOpen: boolean;
  sidebarView: 'menu' | 'search' | 'routes';
  toggleSidebar: () => void;
  setSidebarView: (view: 'menu' | 'search' | 'routes') => void;
}

export const useAppStore = create<AppState>((set) => ({
  isSidebarOpen: false,
  sidebarView: 'menu',
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarView: (view) => set({ sidebarView: view, isSidebarOpen: true }),
}));
