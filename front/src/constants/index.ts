const normalizeBase = (base: string) => base.replace(/\/$/, '');

const rawApiBase = import.meta.env.VITE_API_BASE_URL || '/api';
export const API_BASE_URL = normalizeBase(rawApiBase);

export const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};

const resolveWsBase = (): string => {
  const explicit = import.meta.env.VITE_WS_BASE_URL;
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
