FROM python:3.13-slim

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN pip install uv


# Copy dependency files for build (for better Docker layer caching)
COPY pyproject.toml uv.lock* README.md ./

# Install Python dependencies using uv
RUN uv sync --dev

# Install OpenAI Codex globally
RUN npm install -g @openai/codex

# Copy application code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
