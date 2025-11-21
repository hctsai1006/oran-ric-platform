# ns-O-RAN Bridge for E2-Simulator
# Purpose: Bridge between ns-O-RAN and E2-simulator for UAV integration

FROM python:3.11-slim

LABEL maintainer="O-RAN Project"
LABEL description="ns-O-RAN Bridge for E2-Simulator Integration"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bridge code
COPY src/ ./

# Run bridge
CMD ["python", "-u", "ns_oran_bridge.py", "--e2-host", "e2-simulator.ricxapp.svc.cluster.local", "--e2-port", "8080"]
