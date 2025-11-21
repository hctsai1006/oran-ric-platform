# Multi-stage Dockerfile for RIC Dashboard
# Stage 1: Build Angular application
# Stage 2: Build Python API Gateway and serve Angular

# Stage 1: Build Angular Frontend
FROM node:20-alpine AS angular-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build Angular application for production
RUN npm run build -- --configuration production

# Stage 2: Python API Gateway + Nginx
FROM python:3.11-slim

# Install nginx and supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy API Gateway files
COPY api-gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api-gateway/app.py ./
COPY api-gateway/beam-ui ./beam-ui

# Copy built Angular application from previous stage
COPY --from=angular-builder /app/dist/ric-dashboard/browser /usr/share/nginx/html

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/sites-enabled/default

# Configure Supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories
RUN mkdir -p /var/log/flask /var/log/nginx &&     chmod 755 /var/log/flask /var/log/nginx

# Expose ports
# 80 for Nginx (serving Angular + reverse proxy)
# 5000 for Flask API (internal)
EXPOSE 80 5000

# Start Supervisor (manages both Nginx and Flask)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
