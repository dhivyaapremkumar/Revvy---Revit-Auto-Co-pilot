# frontend/Dockerfile
# Multi-stage build for the REVVY React + TypeScript + Vite frontend.
#
# ASSUMPTIONS (verify once FRONTEND-AGENT finishes scaffolding):
#   - frontend/package.json defines a "build" script (`vite build`) that
#     outputs to frontend/dist (Vite's default outDir).
#   - Static assets are served by nginx in production; VITE_API_URL is baked
#     in at build time (Vite env vars are compile-time, not runtime) via
#     the build arg below, or via a .env file present at build context root.

# ---- Stage 1: build ------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install deps first for better layer caching.
COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---- Stage 2: runtime (static serve via nginx) ---------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
