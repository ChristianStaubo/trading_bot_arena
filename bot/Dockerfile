FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for bot (including GUI automation packages for Linux)
RUN apt-get update && apt-get install -y \
    netcat-traditional \
    python3-tk \
    python3-dev \
    scrot \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy uv configuration files from local bot directory
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies (including GUI automation packages for Linux)
RUN uv sync --frozen --no-dev

# Copy bot code (when building from bot/ directory)
COPY . ./bot/

# Copy and make entrypoint executable
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"] 