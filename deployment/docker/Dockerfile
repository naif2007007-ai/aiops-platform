# ============================================================
# Dockerfile — AI-Ops Platform Dashboard
# Builds a minimal Python 3.11 image running Streamlit.
# Used by AWS App Runner (source: ECR image).
# ============================================================

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cache optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY setup/     ./setup/
COPY dashboard/ ./dashboard/

# Streamlit config — disable telemetry, set port
RUN mkdir -p /root/.streamlit
RUN printf '[server]\nport = 8080\nenableCORS = false\nheadless = true\n\
[browser]\ngatherUsageStats = false\n' > /root/.streamlit/config.toml

EXPOSE 8080

# Entry point
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8080", "--server.address=0.0.0.0"]
