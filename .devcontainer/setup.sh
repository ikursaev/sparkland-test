#!/usr/bin/env sh

# Dev Container Setup Script
echo "🚀 Setting up Crypto Converter development environment..."

# Ensure we're in the right directory
cd /app

# Ensure Codex home exists
echo "📁 Ensuring CODEX_HOME directory exists..."
mkdir -p "${CODEX_HOME:-.codex}"

# Ensure consistent Git line endings inside the container (use LF)
echo "🔧 Configuring Git EOL conversion (autocrlf=input, eol=lf)..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git config core.autocrlf input || true
    git config core.eol lf || true
else
    echo "ℹ️ Not a Git repository. Skipping Git config."
fi

# Copy dev container environment if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Setting up environment configuration..."
    cp .devcontainer/.env.devcontainer .env
    echo "✅ Environment configuration copied from .devcontainer/.env.devcontainer"
fi

# Install Python dependencies with uv
echo "📦 Installing Python dependencies..."
uv sync --dev

# Install Node.js dependencies (OpenAI Codex)
echo "📦 Installing Node.js dependencies..."
npm install -g @openai/codex

# Set up pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🔧 Installing pre-commit hooks..."
    uv run pre-commit install
fi

# Run initial code quality checks
echo "🔍 Running initial code quality checks..."
uv run ruff check . || echo "⚠️  Ruff found some issues - you may want to fix them"
uv run ruff format . || echo "⚠️  Ruff formatting failed"

# Run tests to ensure everything is working
echo "🧪 Running tests..."
uv run pytest tests/ -v || echo "⚠️  Some tests failed - check the output above"
