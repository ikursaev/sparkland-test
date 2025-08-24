FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install uv and use it to install dependencies directly to system Python
RUN pip install uv && \
    uv pip install --system --requirement pyproject.toml

# Copy application code
COPY . .

# Create a volume for the database
VOLUME ["/app/data"]

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/quotes.db

# Expose the API port
EXPOSE 8000

# Default command (can be overridden)
CMD ["python", "run.py", "api"]

