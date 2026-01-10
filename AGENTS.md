# AGENTS.md - Grokomation Codebase Guide for AI Agents

This document provides essential information for AI agents working on the Grokomation codebase. Grokomation is a Python-based FastAPI application that manages isolated development environments for debugging, using Docker containers and Git worktrees.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Build Commands](#build-commands)
3. [Test Commands](#test-commands)
4. [Lint and Format Commands](#lint-and-format-commands)
5. [Code Style Guidelines](#code-style-guidelines)
6. [Additional Rules](#additional-rules)

## Project Overview
- **Language**: Python 3.14+
- **Framework**: FastAPI with Uvicorn
- **Dependency Management**: uv
- **Containerization**: Docker
- **Key Components**:
  - `src/grokomation/main.py`: Main FastAPI app with endpoints for setup, proxy, cleanup
  - `src/grokomation/opencode.py`: OpenAPI spec fetching and validation
  - `src/grokomation/config.py`: Pydantic settings configuration
  - `src/grokomation/processes.py`: Process management utilities
  - `Dockerfile`: Multi-stage build for production container
  - `pyproject.toml`: Project configuration with dependencies

## Build Commands

### Full Build
```bash
# Build Docker image
docker build --build-arg HOST_UID=$(id -u) -t grokomation:latest .

# Build with specific UID (for SSH key access)
docker build --build-arg HOST_UID=1002 -t grokomation:latest .
```

### Development Build
```bash
# Install dependencies locally
uv sync

# Run locally (requires manual setup of env vars)
uv run uvicorn src.grokomation.main:app --host 0.0.0.0 --port 8000
```

### Clean Build
```bash
# Remove build artifacts
docker system prune -f
uv cache clean
```

## Test Commands

### Run All Tests
```bash
# Using pytest (if tests exist)
uv run pytest

# With coverage
uv run pytest --cov=src/grokomation --cov-report=html
```

### Run Single Test
```bash
# Run specific test file
uv run pytest tests/test_file.py

# Run specific test function
uv run pytest tests/test_file.py::test_function_name

# Run tests in class
uv run pytest tests/test_file.py::TestClass::test_method

# With verbose output
uv run pytest -v tests/test_file.py::test_function_name
```

### Test Configuration
- **Framework**: pytest
- **Coverage**: pytest-cov
- **Test Directory**: `tests/` (create if not exists)
- **Mocking**: Use `pytest-mock` for mocking
- **Async Tests**: Use `pytest-asyncio` for async test functions

## Lint and Format Commands

### Linting
```bash
# Using ruff (recommended)
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix

# Check specific file
uv run ruff check src/grokomation/main.py
```

### Formatting
```bash
# Format code with ruff
uv run ruff format .

# Check formatting without changes
uv run ruff format . --check
```

### Type Checking
```bash
# Using mypy
uv run mypy src/

# With strict mode
uv run mypy src/ --strict
```

### Pre-commit Hooks
```bash
# Install pre-commit
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Code Style Guidelines

### General Principles
- **Readability First**: Code should be self-documenting
- **Consistency**: Follow existing patterns in the codebase
- **Performance**: Optimize for FastAPI's async nature
- **Security**: Validate inputs, use secure defaults
- **Documentation**: Add docstrings to functions and classes

### Python Version and Imports
- **Version**: Python 3.14+ (use modern features like `dict` type hints)
- **Import Order**:
  ```python
  # Standard library
  import os
  from typing import Dict, List

  # Third-party
  from fastapi import FastAPI
  import httpx

  # Local imports
  from grokomation.config import settings
  ```
- **Import Style**: Use absolute imports for local modules
- **Avoid**: `from module import *`

### Type Hints
- **Required**: Use type hints for all function parameters and return values
- **Modern Syntax**: Use `dict`, `list`, `tuple` instead of `Dict`, `List`, `Tuple` (Python 3.9+)
- **Optional Types**: Use `Optional[T]` or `T | None`
- **Generic Types**: Use `TypeVar` for generics
- **Example**:
  ```python
  async def get_data(id: int) -> dict[str, str] | None:
      pass
  ```

### Naming Conventions
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules**: `snake_case.py`
- **Private Members**: Prefix with `_` (e.g., `_helper_function`)
- **API Endpoints**: Use hyphens in paths (e.g., `/health-check`)

### Async/Await
- **Use Async**: For I/O operations, database calls, HTTP requests
- **Context Managers**: Use `async with` for async resources
- **Example**:
  ```python
  async with httpx.AsyncClient() as client:
      response = await client.get(url)
  ```

### Error Handling
- **HTTP Exceptions**: Use `fastapi.HTTPException` for API errors
- **Custom Exceptions**: Define in relevant modules (e.g., `InvalidRequestException` in `opencode.py`)
- **Logging**: Use `logging` module, not `print`
- **Validation**: Use Pydantic models for request/response validation
- **Example**:
  ```python
  try:
      result = await risky_operation()
  except ValueError as e:
      logger.error(f"Operation failed: {e}")
      raise HTTPException(400, "Invalid input")
  ```

### FastAPI Specific
- **Route Organization**: Group related routes, use tags for documentation
- **Dependencies**: Use dependency injection for shared logic
- **Middleware**: Add middleware for logging, CORS, etc.
- **Response Models**: Define Pydantic models for responses
- **Example**:
  ```python
  @app.post("/setup", tags=["instances"])
  async def setup(data: SetupRequest) -> SetupAPIResponse:
      # Implementation
      pass
  ```

### Database/Models
- **ORM**: Use SQLAlchemy or similar if needed
- **Migrations**: Use Alembic for schema changes
- **Models**: Define in separate modules

### Security
- **Input Validation**: Always validate and sanitize inputs
- **Secrets**: Use environment variables, never hardcode
- **CORS**: Configure appropriately
- **Rate Limiting**: Implement if needed

### Testing
- **Unit Tests**: Test individual functions
- **Integration Tests**: Test API endpoints
- **Fixtures**: Use pytest fixtures for setup
- **Mocking**: Mock external dependencies
- **Coverage**: Aim for 80%+ coverage

### Documentation
- **Docstrings**: Use Google-style docstrings
- **README**: Keep updated with setup and usage instructions
- **API Docs**: Rely on FastAPI's auto-generated docs

### File Structure
```
grokomation/
├── src/grokomation/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── config.py        # Settings
│   ├── opencode.py      # OpenAPI utilities
│   └── processes.py     # Process management
├── tests/
│   └── ...              # Test files
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── README.md
```

### Commit Messages
- **Format**: `type(scope): description`
- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Example**: `feat(proxy): add OpenAPI validation`

### Performance
- **Async First**: Use async for scalability
- **Caching**: Implement caching for expensive operations
- **Profiling**: Use `cProfile` or `aiohttp-devtools` for analysis

### Docker
- **Multi-stage**: Keep builder/final separation
- **Security**: Run as non-root user
- **Healthchecks**: Include in Dockerfile

## Additional Rules

### No Cursor or Copilot Rules Found
No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files were found in the repository. If added in the future, incorporate their guidelines here.

### AI Agent Best Practices
- **Read Existing Code**: Understand patterns before making changes
- **Run Tests**: Ensure changes don't break functionality
- **Use Type Hints**: Maintain type safety
- **Document Changes**: Update this file if introducing new patterns
- **Ask for Clarification**: When in doubt, seek human input

This guide should be updated as the codebase evolves. Last updated: 2026-01-10