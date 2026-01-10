import psutil

from httpx import AsyncClient, Timeout, TimeoutException, HTTPStatusError, ConnectError
from pydantic import BaseModel


def list_opencode_processes() -> list[dict[str, int | str | None]]:
    instances: list[dict[str, int | str | None]] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = proc.info["cmdline"] or []
            if "opencode" in cmd and "serve" in cmd:
                # Try to extract port from cmdline (e.g., --port 4106)
                port = None
                for i, arg in enumerate(cmd):
                    if arg == "--port" and i + 1 < len(cmd):
                        port = int(cmd[i + 1])
                        break
                instances.append(
                    {"pid": proc.pid, "port": port, "cmdline": " ".join(cmd)}
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return instances


default_headers = {"content-type": "application/json"}


class OpenCodeHealthResponse(BaseModel):
    healthy: bool
    version: str


class OpenCodeHealthError(Exception): ...


async def check_opencode_health(
    port: int, timeout: float = 1.0
) -> OpenCodeHealthResponse:
    """Async check if port is running OpenCode server by hitting /global/health."""
    url = f"http://127.0.0.1:{port}/global/health"
    try:
        async with AsyncClient() as client:
            resp = await client.request(
                method="GET", url=url, timeout=Timeout(timeout), headers=default_headers
            )
            if resp.status_code == 200:
                return OpenCodeHealthResponse(**resp.json())
            raise OpenCodeHealthError(
                f"Unexpected status code {resp.status_code} from OpenCode health endpoint"
            )
    except (HTTPStatusError, TimeoutException, ConnectError) as e:
        raise OpenCodeHealthError(
            f"Failed to connect to OpenCode server on port {port}: {str(e)}"
        )
