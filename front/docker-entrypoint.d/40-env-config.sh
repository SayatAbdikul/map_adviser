#!/bin/sh
set -eu

js_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

API_BASE_URL_VALUE="$(js_escape "${API_BASE_URL:-/api}")"
WS_BASE_URL_VALUE="$(js_escape "${WS_BASE_URL:-}")"
MAP_API_KEY_VALUE="$(js_escape "${MAP_API_KEY:-${VITE_2GIS_API_KEY:-}}")"

cat > /usr/share/nginx/html/env-config.js <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL_VALUE}",
  WS_BASE_URL: "${WS_BASE_URL_VALUE}",
  MAP_API_KEY: "${MAP_API_KEY_VALUE}"
};
EOF
