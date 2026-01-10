import time
import httpx


class InvalidRequestException(Exception):
    """Raised when a request does not match the OpenAPI specification."""


_spec_cache: dict[tuple[str, int], tuple[dict, float]] = {}


async def get_openapi_spec(hostname: str, port: int, ttl: int = 600) -> dict:
    """Fetch OpenAPI spec with caching (default 10 minutes)."""
    key = (hostname, port)
    now = time.time()

    if key in _spec_cache:
        spec, timestamp = _spec_cache[key]
        if now - timestamp < ttl:
            return spec

    url = f"http://{hostname}:{port}/doc"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        spec = response.json()

    _spec_cache[key] = (spec, now)
    return spec


def validate_request(spec: dict, method: str, path: str) -> None:
    """Validate that the method and path are allowed according to the OpenAPI spec."""
    if "paths" not in spec:
        raise InvalidRequestException("Invalid OpenAPI spec: no paths defined")

    if path not in spec["paths"]:
        raise InvalidRequestException(f"Path '{path}' not found in OpenAPI spec")

    allowed_methods = [m.lower() for m in spec["paths"][path].keys()]
    if method.lower() not in allowed_methods:
        raise InvalidRequestException(
            f"Method '{method}' not allowed for path '{path}'"
        )


async def check_request_validity(
    hostname: str, port: int, method: str, path: str
) -> None:
    """Fetch the OpenAPI spec and validate the request."""
    spec = await get_openapi_spec(hostname, port)
    validate_request(spec, method, path)
