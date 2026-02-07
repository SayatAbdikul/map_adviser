# Frontend Dockerfile (build + nginx serve)

FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.25-alpine AS runner
WORKDIR /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/40-env-config.sh /docker-entrypoint.d/40-env-config.sh
RUN chmod +x /docker-entrypoint.d/40-env-config.sh
COPY --from=builder /app/dist ./

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
