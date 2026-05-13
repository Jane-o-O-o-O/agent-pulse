FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install package with web extras
RUN pip install --no-cache-dir -e ".[web]"

# Expose web dashboard port
EXPOSE 8765

# Default: run CLI dashboard
ENTRYPOINT ["agent-pulse"]

# Default args: show dashboard
CMD []
