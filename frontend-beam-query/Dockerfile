FROM python:3.11-slim

LABEL description="Beam Query UI with WSGI proxy server"
LABEL version="1.0.0"

WORKDIR /app

# Install gunicorn for WSGI
RUN pip install --no-cache-dir gunicorn

# Copy application files
COPY wsgi_app.py .
COPY index.html .
COPY app.js .

# Create non-root user
RUN useradd -m -u 1000 webapp && \
    chown -R webapp:webapp /app

USER webapp

# Expose port
EXPOSE 8888

# Run with gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "4", "--timeout", "30", "wsgi_app:application"]
