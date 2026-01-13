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
        git \
	openssh-client \
	curl \
	ca-certificates \
	gpg \
	jq \
	ripgrep \
	fd-find \
	fzf \
	bat \
	git-delta \
	tokei \
	iproute2 \
	htop \
	procps \
	strace \
	lsof \
	yq \
	redis-tools \
	&& \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends gh && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    ln -s /usr/bin/batcat /usr/local/bin/bat && \
    ln -s /usr/bin/fdfind /usr/local/bin/fd


COPY --from=builder /app /app

# Make these available for the AI
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"


EXPOSE 8000

RUN mkdir -p /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh && \
    echo "Host github.com\n  IdentityFile /home/appuser/.ssh/deploy_key\n  StrictHostKeyChecking accept-new" > /home/appuser/.ssh/config && \
    chmod 600 /home/appuser/.ssh/config


ARG UID=1000
ARG GID=1000
ARG GIT_USER="Grokomation Service"
ARG GIT_EMAIL="grokomation@yourdomain.com"

RUN groupadd -g $GID appgroup && \
    useradd -u $UID -g appgroup -m -d /home/appuser -s /bin/bash appuser && \
    mkdir -p /home/appuser/.ssh && \
    ssh-keyscan -t ed25519 github.com >> /home/appuser/.ssh/known_hosts && \
    chown -R appuser:appgroup /home/appuser && \
    chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/known_hosts && \
    mkdir -p /repo && \
    mkdir -p /app/worktrees && \
    chown -R appuser:appgroup /repo && \
    chown -R appuser:appgroup /app/worktrees
USER appuser

# Preconfigure git for non-root user (appuser)
RUN git config --global user.name "$GIT_USER" && \
    git config --global user.email "$GIT_EMAIL" && \
    git config --global --add safe.directory '*' && \
    git config --global init.defaultBranch master && \
    git config --global push.default simple && \

    echo "Git global config initialized for ${USER}"

    # Optional: if you ever want signed commits (needs gpg setup)
    # git config --global commit.gpgsign true
    # git config --global user.signingkey YOUR_KEY_ID

RUN mkdir -p ~/.local/bin && \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Install opencode into ~/.local/bin instead of ~/.opencode/bin
RUN curl -fsSL https://opencode.ai/install | \
    XDG_BIN_HOME=$HOME/.local/bin bash

ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PROJECT_PATH="/repo" \
    WORKTREE_BASE="/app/worktrees" \
    PORT=8000 \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy

# Pre-install the most common tools OpenCode uses
RUN uv tool install \
    ruff \
    ty \
    pytest-cov \
    bandit \
    pytest-benchmark \
    memory-profiler \
    line-profiler \
    py-spy \
    && echo "Pre-installed: ruff, ty, uv" >> ~/.bashrc

RUN pip install --no-cache-dir \
    pre-commit \
    pytest \
    pytest-asyncio

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1 || curl -f http://localhost:8000 || exit 1

CMD ["uvicorn", "src.grokomation.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers"]
