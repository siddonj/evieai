FROM node:20-alpine AS builder
WORKDIR /app
COPY web_ui/package.json web_ui/package-lock.json ./
RUN npm ci
COPY web_ui/ .
RUN npm run build

FROM nginx:alpine
COPY web_ui/nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
