/// <reference types="vite/client" />

interface Window {
  __APP_CONFIG__?: {
    API_BASE_URL?: string;
    WS_BASE_URL?: string;
    MAP_API_KEY?: string;
  };
}
