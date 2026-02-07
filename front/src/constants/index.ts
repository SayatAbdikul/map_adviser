const normalizeBase = (base: string) => base.replace(/\/$/, '');

const runtimeConfig = typeof window !== 'undefined' ? window.__APP_CONFIG__ : undefined;

const rawApiBase = runtimeConfig?.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || '/api';
export const API_BASE_URL = normalizeBase(rawApiBase);

export const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};

const resolveWsBase = (): string => {
  const explicit = runtimeConfig?.WS_BASE_URL || import.meta.env.VITE_WS_BASE_URL;
  if (explicit) return normalizeBase(explicit);

  if (API_BASE_URL.startsWith('http')) {
    return API_BASE_URL.replace(/^http/, 'ws');
  }

  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin.replace(/^http/, 'ws');
  }

  return 'ws://localhost:8000';
};

export const WS_BASE_URL = resolveWsBase();
