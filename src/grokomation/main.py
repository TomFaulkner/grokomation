from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import Field
import logging
import os
import subprocess
from typing import cast

from fastapi import FastAPI, Request, Response, HTTPException, Query
import httpx
from httpx import AsyncClient
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from grokomation.config import settings
from grokomation import processes
from grokomation.opencode import check_request_validity, InvalidRequestException
from grokomation.database import (
    init_db,
    insert_instance,
    delete_instance,
    get_all_instances,
    get_instance_port,
    insert_chat,
)


settings = settings  # loading for settings validation for shell scripts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Runs before the app starts accepting requests
    uid = os.getuid()
    if uid == 0:
        raise RuntimeError("Security error: FastAPI is running as root (UID 0)!")

    logger.info(f"Running as UID {uid} (non-root)")

    # Clone repo if not present
    repo_path = "/repo"
    if not os.path.exists(os.path.join(repo_path, ".git")):
        repo_url = os.getenv("REPO_URL")
        if repo_url:
            logger.info(f"Cloning repo from {repo_url} to {repo_path}")
            subprocess.run(
                ["git", "clone", repo_url, repo_path], check=True, timeout=120
            )
            logger.info("Repo cloned successfully")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    yield  # The app runs normally here


app = FastAPI(lifespan=lifespan)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class TracebackEntry(BaseModel):
    file: str
    line: int
    function: str
    stack_trace: str


class SetupRequest(BaseModel):
    correlation_id: str | None = None
    now: datetime = Field(default_factory=datetime.utcnow)
    traceback: TracebackEntry | None = None
    error: str
    request_url: str | None = None
    request_method: str | None = None
    host: str
    type: str


class SetupShellResponse(BaseModel):
    port: int
    worktree: str
    prod_hash: str
    master_hash: str
    compare_advice: str
    matches_master: bool
    pid_file: str
    pid: int


class SetupAPIResponse(BaseModel):
    correlation_id: str | None = None
    status: str


@app.post("/instances", tags=["instances"])
async def setup(data: SetupRequest) -> SetupAPIResponse:
    if not data.correlation_id:
        data.correlation_id = f"corr-{int(datetime.utcnow().timestamp() * 1000)}"
    try:
        results = subprocess.run(
            ["./setup_env.sh", data.correlation_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        logger.debug("Shell stdout: %s", results.stdout)
        logger.error("Shell stderr: %s", results.stderr)
        shell_response = SetupShellResponse.model_validate_json(
            results.stdout.splitlines()[-1]
        )
    except subprocess.CalledProcessError as e:
        logging.exception(f"Setup failed: {cast('str', e.stderr)}")
        raise HTTPException(500, f"Setup failed: {e}")

    insert_instance(data.correlation_id, shell_response.port)
    logger.info(
        f"Setup complete for correlation_id={data.correlation_id} on port {shell_response.port}"
    )
    logger.info("Shell response: %s", shell_response)
    return SetupAPIResponse(
        **{"status": "setup_complete", "correlation_id": data.correlation_id}
    )


@app.delete("/instances/{corr_id}", tags=["instances"])
async def cleanup(corr_id: str):
    try:
        results = subprocess.run(
            ["./cleanup_env.sh", corr_id],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug("cleanup_env.sh stdout: %s", results.stdout)
        logger.debug("cleanup_env.sh stderr: %s", results.stderr)
    except subprocess.CalledProcessError as e:
        logging.exception(f"Cleanup failed: {cast('str', e.stderr)}")
        raise HTTPException(500, f"Cleanup failed: {e}")

    delete_instance(corr_id)
    return {"status": "cleaned"}


@app.get("/instances", tags=["instances"])
def get_instances() -> dict[str, int]:
    return get_all_instances()


@app.post("/instances/{corr_id}/chat", tags=["instances"])
async def save_chat(corr_id: str, chat_data: dict):
    """Save chat data for an instance."""
    # Verify instance exists
    if get_instance_port(corr_id) is None:
        raise HTTPException(404, "Instance not found")

    # Convert dict to JSON string and save
    import json

    chat_json = json.dumps(chat_data)
    insert_chat(corr_id, chat_json)
    return {"status": "chat_saved"}


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/proc/check_port", tags=["processes"])
async def check_port(port: int) -> processes.OpenCodeHealthResponse:
    try:
        return await processes.check_opencode_health(port)
    except processes.OpenCodeHealthError as e:
        raise HTTPException(502, str(e))


@app.get("/proc/list_opencode", tags=["processes"])
def list_opencode() -> list[dict[str, int | str | None]]:
    return processes.list_opencode_processes()


class KillProcessResponse(BaseModel):
    success: bool
    message: str


@app.delete("/proc/{pid}", tags=["processes"])
def kill_process(pid: int) -> KillProcessResponse:
    success, msg = processes.kill_opencode_process(pid)
    return KillProcessResponse(success=success, message=msg)


# Proxy endpoints


async def _proxy_request(corr_id: str, path: str, request: Request) -> Response:
    port = get_instance_port(corr_id)
    if port is None:
        raise HTTPException(404, "No active session")
    if not path.startswith("/"):
        path = "/" + path
    try:
        await check_request_validity("localhost", port, request.method, path)
    except InvalidRequestException as e:
        raise HTTPException(422, str(e))
    except httpx.RequestError as e:
        raise HTTPException(502, f"Error fetching OpenAPI spec: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error validating request: {str(e)}")
    url = f"http://localhost:{port}{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    headers["content-type"] = "application/json"
    async with AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


@app.get("/instances/{corr_id}/proxy", tags=["instances"])
async def proxy_get(
    corr_id: str,
    request: Request,
    path: str = Query("/", description="The path to proxy to the opencode instance"),
):
    return await _proxy_request(corr_id, path, request)


@app.post("/instances/{corr_id}/proxy", tags=["instances"])
async def proxy_post(
    corr_id: str,
    request: Request,
    path: str = Query("/", description="The path to proxy to the opencode instance"),
):
    return await _proxy_request(corr_id, path, request)


@app.put("/instances/{corr_id}/proxy", tags=["instances"])
async def proxy_put(
    corr_id: str,
    request: Request,
    path: str = Query("/", description="The path to proxy to the opencode instance"),
):
    return await _proxy_request(corr_id, path, request)


@app.patch("/instances/{corr_id}/proxy", tags=["instances"])
async def proxy_patch(
    corr_id: str,
    request: Request,
    path: str = Query("/", description="The path to proxy to the opencode instance"),
):
    return await _proxy_request(corr_id, path, request)


@app.delete("/instances/{corr_id}/proxy", tags=["instances"])
@limiter.limit("5/minute")
async def proxy_delete(
    corr_id: str,
    request: Request,
    path: str = Query("/", description="The path to proxy to the opencode instance"),
):
    return await _proxy_request(corr_id, path, request)
