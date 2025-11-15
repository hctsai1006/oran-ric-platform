# E2 Simulator Dockerfile
# 作者: 蔡秀吉 (thc1006)
# 日期: 2025-11-15

FROM python:3.11-slim

LABEL maintainer="Tsai Hsiu-Chi (thc1006)"
LABEL description="E2 Simulator for O-RAN RIC Platform Testing"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator code
COPY src/ ./

# Run simulator
CMD ["python", "-u", "e2_simulator.py"]
