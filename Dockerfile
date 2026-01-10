# -------------------
# Builder Stage
# -------------------
FROM python:3.14-slim AS builder

# Install uv globally (as root)
RUN pip install --no-cache-dir uv==0.9.17

WORKDIR /app

# Copy only dependency files first → great layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into isolated environment
RUN uv sync --frozen --all-extras --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --frozen --all-extras

# -------------------
# Final Runtime Stage
# -------------------
FROM python:3.14-slim

# Create non-root user & group
RUN groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -m -d /app appuser

# Install uv in final stage
RUN pip install --no-cache-dir uv==0.9.17

# Install Git for script dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy uv cache & installed packages from builder
COPY --from=builder /root/.cache/uv /app/.cache/uv
COPY --from=builder /app /app

# Chown everything to HOST_UID
RUN chown -R ${HOST_UID}:appgroup /app /app/.cache

# Create writable directories for appuser (but since user overridden, for worktrees)
RUN mkdir -p /app/worktrees /app/.ssh && \
    chown -R ${HOST_UID}:appgroup /app/worktrees /app/.ssh
COPY --from=builder --chown=appuser:appgroup /root/.cache/uv /app/.cache/uv
COPY --from=builder --chown=appuser:appgroup /app /app

WORKDIR /app

# Switch to non-root user
USER 1001

# Build args
ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT
ARG HOST_UID=1001

# Chown /app to HOST_UID for proper access when user is set in Compose
RUN chown -R ${HOST_UID}:appgroup /app

# Expose port
EXPOSE 8000

# Healthcheck (optional but recommended)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn directly (cleaner shutdown)
CMD ["uv", "run", "uvicorn", "src.grokomation.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
