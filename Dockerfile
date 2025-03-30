FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Create a health check endpoint
RUN mkdir -p /app/_stcore
RUN echo '{"status": "ok"}' > /app/_stcore/health

# Run Streamlit
ENTRYPOINT ["./run.sh"]
# CMD ["app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1