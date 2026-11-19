# syntax=docker/dockerfile:1
FROM node:24.22.3-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Development: Vite dev server, source bind-mounted by docker-compose.yml ---
FROM base AS development
COPY . .
USER node
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]

# --- Build static assets ---
FROM base AS build
COPY . .
RUN npm run build

# --- Production: static files served by unprivileged Nginx ---
FROM nginxinc/nginx-unprivileged:1.31.7-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
