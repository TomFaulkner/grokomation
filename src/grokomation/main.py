import logging
import subprocess
from typing import cast
from urllib.parse import unquote

from fastapi import FastAPI, Request, Response, HTTPException
from httpx import AsyncClient
from pydantic import BaseModel

from grokomation.config import settings
from grokomation import processes
from grokomation.opencode import check_request_validity, InvalidRequestException

settings = settings  # loading for settings validation for shell scripts

app = FastAPI()
instances: dict[str, int] = {}  # correlation_id → internal_port
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SetupRequest(BaseModel):
    correlation_id: str


class SetupShellResponse(BaseModel):
    port: int
    worktree: str
    prod_hash: str
    master_hash: str
    compare_advice: str
    matches_master: bool


class SetupAPIResponse(BaseModel):
    status: str
    corr_id: str


@app.post("/setup")
async def setup(data: SetupRequest) -> SetupAPIResponse:
    try:
        results = subprocess.run(
            ["./setup_env.sh", data.correlation_id],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug("Shell stdout: %s", results.stdout)
        logger.error("Shell stderr: %s", results.stderr)
        shell_response = SetupShellResponse.model_validate_json(
            results.stdout.splitlines()[-1]
        )
    except subprocess.CalledProcessError as e:
        logging.exception(f"Setup failed: {cast('str', e.stderr)}")
        raise HTTPException(500, f"Setup failed: {e}")

    instances[data.correlation_id] = shell_response.port
    return SetupAPIResponse(
        **{"status": "setup_complete", "corr_id": data.correlation_id}
    )


@app.api_route("/proxy/{corr_id}/{path:path}", methods=["GET", "POST"])
async def proxy(corr_id: str, path: str, request: Request):
    if corr_id not in instances:
        raise HTTPException(404, "No active session")
    path = unquote(path)
    try:
        await check_request_validity(
            "localhost", instances[corr_id], request.method, path
        )
    except InvalidRequestException as e:
        raise HTTPException(422, str(e))
    url = f"http://localhost:{instances[corr_id]}/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    headers["accept"] = "application/json"
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


# Cleanup endpoint (called by n8n when "DONE")
@app.post("/cleanup/{corr_id}")
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

    _ = instances.pop(corr_id, None)
    return {"status": "cleaned"}


@app.get("/instances")
def get_instances() -> dict[str, int]:
    return instances


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/proc/check_port")
async def check_port(port: int) -> processes.OpenCodeHealthResponse:
    return await processes.check_opencode_health(port)
