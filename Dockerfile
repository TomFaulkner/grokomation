# -------------------
# Builder Stage
# -------------------
FROM python:3.14-slim AS builder

RUN pip install --no-cache-dir uv==0.9.17

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install dependencies into isolated environment
RUN uv sync --frozen --all-extras --no-install-project

COPY . .

RUN uv sync --frozen --all-extras


# -------------------
# Final Runtime Stage
# -------------------
FROM python:3.14-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

USER 1000

EXPOSE 8000

RUN mkdir -p /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh && \
    echo "Host github.com\n  IdentityFile /home/appuser/.ssh/id_ed25519\n  StrictHostKeyChecking accept-new" > /home/appuser/.ssh/config && \
    chmod 600 /home/appuser/.ssh/config

RUN ssh-keyscan -t ed25519 github.com >> /home/appuser/.ssh/known_hosts

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1 || curl -f http://localhost:8000 || exit 1

CMD ["uvicorn", "src.grokomation.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers"]
