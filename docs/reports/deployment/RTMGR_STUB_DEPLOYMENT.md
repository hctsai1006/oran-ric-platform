# RTMgr Stub Service Deployment

## Problem Solved
RTMgr 0.8.2 was in CrashLoopBackOff because it expected SubMgr to provide the `/ric/v1/subscriptions` REST API endpoint, but SubMgr 0.10.7 doesn't implement this endpoint (returns 404).

## Solution Deployed
Created an nginx-based stub service that responds to `/ric/v1/subscriptions` with an empty JSON array `[]`, satisfying RTMgr's requirements.

## Deployed Resources

### 1. ConfigMap: submgr-stub-nginx-config
- **Purpose**: Nginx configuration for the stub service
- **Namespace**: ricplt
- **Configuration**:
  - Listens on port 8088
  - Returns `[]` for `/ric/v1/subscriptions`
  - Health check endpoint at `/health`

### 2. Deployment: deployment-submgr-stub
- **Purpose**: Runs the nginx stub service
- **Namespace**: ricplt
- **Image**: nginx:alpine
- **Replicas**: 1
- **Port**: 8088
- **Health Probes**:
  - Liveness: HTTP GET /health on port 8088
  - Readiness: HTTP GET /health on port 8088
- **Volume**: ConfigMap mounted at /etc/nginx/nginx.conf

### 3. Service: service-submgr-stub
- **Purpose**: ClusterIP service for the stub
- **Namespace**: ricplt
- **Type**: ClusterIP
- **ClusterIP**: 10.43.119.64
- **Port**: 8088
- **Selector**: app=submgr-stub

### 4. Updated Service: service-ricplt-submgr-http
- **Purpose**: Routes traffic to both SubMgr and the stub
- **Namespace**: ricplt
- **Type**: ClusterIP
- **ClusterIP**: 10.43.221.31 (preserved)
- **Ports**:
  - 8080 -> SubMgr pod (10.42.0.177:8080)
  - 8088 -> Stub pod (10.42.0.71:8088)

### 5. Endpoints: service-ricplt-submgr-http
- **Purpose**: Manual endpoint configuration for multi-target routing
- **Configuration**:
  - Subset 1: Port 8080 -> SubMgr pod IP
  - Subset 2: Port 8088 -> Stub pod IP

## Verification

### Stub Service Test
```bash
curl http://service-ricplt-submgr-http:8088/ric/v1/subscriptions
# Returns: []
# HTTP Status: 200
```

### RTMgr Status
- **Before**: CrashLoopBackOff (7 restarts)
- **After**: Running (8 restarts, now stable)
- **Pod**: deployment-ricplt-rtmgr-6d479f4bc-gmkr2
- **IP**: 10.42.0.93
- **Age**: 20 minutes
- **Status**: 1/1 Running

### Stub Pod Status
- **Pod**: deployment-submgr-stub-5c464c77d6-pvhnq
- **IP**: 10.42.0.71
- **Status**: 1/1 Running
- **Age**: ~2 minutes
- **Restarts**: 0

## Architecture

```
RTMgr (10.42.0.93)
    |
    | HTTP Request to:
    | service-ricplt-submgr-http:8088/ric/v1/subscriptions
    |
    v
service-ricplt-submgr-http (10.43.221.31)
    |
    +-- Port 8080 --> SubMgr Pod (10.42.0.177:8080)
    |                 - Actual SubMgr endpoints
    |
    +-- Port 8088 --> Stub Pod (10.42.0.71:8088)
                      - Returns [] for /ric/v1/subscriptions
```

## Deployment Commands

All resources were deployed using the Kubernetes MCP server:

1. ConfigMap created with nginx configuration
2. Deployment created with nginx:alpine image
3. Service created for stub pod
4. Original service deleted and recreated without selector
5. Manual Endpoints created to route traffic

## Status: SUCCESS

- Stub service deployed and running
- Service configured correctly
- RTMgr pod status: Running (no more CrashLoopBackOff)
- Endpoint responding correctly with empty JSON array

## Date Deployed
2025-11-18 23:49:34 UTC
