import logging
import subprocess
from typing import cast

from fastapi import FastAPI, Request, Response, HTTPException
from httpx import AsyncClient
from pydantic import BaseModel

app = FastAPI()
instances: dict[str, int] = {}  # correlation_id → internal_port
logging.basicConfig(level=logging.INFO)
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
            ["setup_env.sh", data.correlation_id],
            check=True,
            capture_output=True,
            text=True,
        )
        # shell_res_json = cast(
        #     "dict[str, str | int | bool]", json.loads(results.stdout.splitlines()[-1])
        # )
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
    url = f"http://localhost:{instances[corr_id]}/{path}"
    async with AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
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
            ["cleanup_env.sh", corr_id],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logging.exception(f"Cleanup failed: {cast('str', e.stderr)}")
        raise HTTPException(500, f"Cleanup failed: {e}")

    instances.pop(corr_id, None)
    return {"status": "cleaned"}
