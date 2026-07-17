# --- build the Vite bundle ---------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# '' = same-origin; nginx proxies the API paths to the validator container.
ARG VITE_VALIDATOR_URL=""
ENV VITE_VALIDATOR_URL=$VITE_VALIDATOR_URL
RUN npm run build

# --- serve with nginx ---------------------------------------------------------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
