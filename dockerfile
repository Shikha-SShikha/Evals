FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# If you need system deps for scientific libs, add them here
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and data
COPY json_dashboard.py merged_results.json ./

# Streamlit config for headless mode
ENV PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLECORS=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose the port (Cloud Run sets $PORT)
CMD ["streamlit", "run", "json_dashboard.py", "--server.port", "8080", "--server.address", "0.0.0.0"]

