# ---- deps ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- dev (used by docker-compose.yml) ----
FROM deps AS dev
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]

# ---- build ----
FROM deps AS build
COPY . .
RUN npm run build

# ---- serve (used by docker-compose.prod.yml) ----
FROM nginx:1.27-alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
