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

# Copy uv cache & installed packages from builder
COPY --from=builder --chown=appuser:appgroup /root/.cache/uv /app/.cache/uv
COPY --from=builder --chown=appuser:appgroup /app /app

WORKDIR /app

# Switch to non-root user
USER 1001

# Build arg for git commit (optional)
ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

# Expose port
EXPOSE 8000

# Healthcheck (optional but recommended)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn directly (cleaner shutdown)
CMD ["uv", "run", "uvicorn", "src.grokomation.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
