# Grokomation

Grokomation is a FastAPI-based service for managing isolated development environments. It automates the setup of Git worktrees for debugging, proxies requests to OpenCode instances, and integrates with external APIs for version tracking.

## Features

- **Automated Environment Setup**: Creates Git worktrees based on production commits.
- **OpenAPI Validation**: Filters proxy requests against the target API's OpenAPI spec.
- **SSH-Based Git Operations**: Supports private repositories via SSH keys.
- **Docker Integration**: Fully containerized with named volumes for persistence.

## Prerequisites

- Docker and Docker Compose
- SSH private key for accessing the target Git repository
- Access to an API endpoint for retrieving production commit hashes

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/grokomation.git
cd grokomation
```

### 2. Build the Docker Image

```bash
docker build --build-arg HOST_UID=$(id -u) -t grokomation:latest .
```

### 3. Configure Docker Compose

Create a `docker-compose.yml` file with the following service configuration:

```yaml
version: '3.8'

volumes:
  grokomation_repo:
  grokomation_worktrees:
  grokomation_tmp:

services:
  grokomation:
    image: grokomation:latest
    restart: unless-stopped
    ports:
      - "8001:8000"  # Expose the proxy port
    volumes:
      - grokomation_repo:/repo  # Named volume for cloned repo
      - grokomation_worktrees:/app/worktrees  # Named volume for worktrees
      - grokomation_tmp:/tmp/opencode-pids
      - /path/to/your/ssh/key:/home/appuser/.ssh/id_rsa:ro  # Mount SSH private key (read-only)
    environment:
      - DEBUG_ENV=.env.debug.template
      - GET_PROD_HASH_COMMAND=curl -s https://your-api-endpoint.com/api/health | jq -r '.version'
      - WORKTREE_BASE=/app/worktrees
      - REPO_URL=git@github.com:your-org/your-repo.git
      - GIT_SSH_COMMAND=ssh -i /home/appuser/.ssh/id_rsa -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/appuser/.ssh/known_hosts
```

**Important Notes**:
- Replace `/path/to/your/ssh/key` with the actual path to your SSH private key on the host.
- The SSH private key must be owned by the user running Docker (typically UID $(id -u)). Ensure correct ownership: `chown $(id -u):$(id -g) /path/to/your/ssh/key`.
- Update `REPO_URL` to your target Git repository.
- Adjust `GET_PROD_HASH_COMMAND` to query your API for the production commit hash.

### 4. Start the Service

```bash
docker-compose up -d
```

### 5. Verify Setup

- Check logs: `docker-compose logs grokomation`
- Health check: `curl http://localhost:8001/health`
- Setup an instance: `curl -X POST http://localhost:8001/instances/setup -d '{"correlation_id": "test123"}'`

## API Endpoints

- `POST /instances/setup`: Initialize a new debugging environment.
- `GET /instances`: List active instances.
- `DELETE /instances/{corr_id}`: Clean up an instance.
- `GET/POST /instances/{corr_id}/proxy/{path:path}`: Proxy requests to the OpenCode instance.
- `GET /health`: Service health check.
- `GET /proc/check_port`: Check OpenCode health on a port.

## Configuration

Environment variables:

- `DEBUG_ENV`: Path to debug environment file (relative to repo root).
- `GET_PROD_HASH_COMMAND`: Command to retrieve production commit hash.
- `WORKTREE_BASE`: Directory for Git worktrees.
- `REPO_URL`: Git repository URL (SSH format).
- `GIT_SSH_COMMAND`: SSH command for Git operations.
- `PROJECT_PATH`: Path to the cloned repository (default: /repo).

## Development

### Local Setup

```bash
uv sync
uv run uvicorn src.grokomation.main:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Troubleshooting

- **Permission Denied on SSH Key**: Ensure the SSH key is owned by the host user running Docker.
- **Git Clone Fails**: Verify SSH key setup and repository access.
- **Port Conflicts**: OpenCode instances use ports 4100-4200; ensure availability.
- **Volume Issues**: Named volumes persist data; inspect with `docker volume ls`.

