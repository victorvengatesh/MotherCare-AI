# Multi-stage build for MotherCare AI Frontend
# Stage 1: Builder
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime serving static files via Nginx
FROM nginx:1.25-alpine

# Copy built application from builder to Nginx server root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom Nginx config for routing fallback & port 3000
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 3000
EXPOSE 3000

# Health check using wget
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
