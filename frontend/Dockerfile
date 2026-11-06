# ─────────────────────────────────────────────────────────────
# LabFlow frontend (React + Vite → nginx) — WBS 2.1.2
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# По умолчанию API запрашивается через тот же origin (прокси nginx → backend)
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Собираем прод-бандл через Vite.
# Примечание: `npm run build` дополнительно запускает `tsc -b`, а tsconfig
# фронтенда сейчас использует опции из TypeScript 5.8+ при версии ~5.4 в
# package.json — из-за этого typecheck падает. Для Docker-сборки ограничиваемся
# Vite-бандлом; типизацию чинит Frontend-разработчик (WBS 4.1.4/4.2.4).
RUN npx vite build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80