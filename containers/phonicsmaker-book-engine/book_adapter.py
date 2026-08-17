"""Omo adapter for the source-compatible PhonicsMaker book engine.

The engine is deliberately injected. Until the source engine has been bound to
Omo's private artifact plane and approved provider secrets, submission fails
closed rather than returning a mock book.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parent
INPUT_SCHEMA = json.loads((ROOT / "schemas/input.json").read_text(encoding="utf-8"))
OUTPUT_SCHEMA = json.loads((ROOT / "schemas/output.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(INPUT_SCHEMA)
Draft202012Validator.check_schema(OUTPUT_SCHEMA)

WORKFLOW_VERSION = "phonicsmaker-core@source-4c31dc2"

SpawnRunner = Callable[[dict[str, Any]], str]
LookupResult = Callable[[str], dict[str, Any]]


def validate_input(payload: Any) -> None:
    Draft202012Validator(INPUT_SCHEMA).validate(payload)


def validate_output(result: Any) -> None:
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)


def create_book_app(
    spawn_runner: SpawnRunner | None = None,
    lookup_result: LookupResult | None = None,
) -> Any:
    """Create the protected Omo-facing FastAPI app.

    `spawn_runner` and `lookup_result` are the only execution seam. Tests inject
    deterministic functions. The live Modal wrapper will bind them to the
    source engine only after the artifact/provider boundary is implemented.
    """
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import JSONResponse

    app = FastAPI(title="phonicsmaker-core", version=WORKFLOW_VERSION)

    @app.post("/v1/runs", status_code=202)
    async def submit(body: Any = Body(...)) -> Any:
        try:
            validate_input(body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        if spawn_runner is None:
            return JSONResponse(
                {
                    "status": "not_ready",
                    "error": {
                        "code": "PHONICSMAKER_ENGINE_NOT_BOUND",
                        "message": "The source engine is not bound to the Omo artifact/provider plane.",
                    },
                },
                status_code=503,
            )

        call_id = spawn_runner(body)
        run_id = str(uuid.uuid4())
        return {
            "run_id": run_id,
            "call_id": call_id,
            "status": "accepted",
            "workflow_version": WORKFLOW_VERSION,
            "result_url": f"/v1/runs/{call_id}",
        }

    @app.get("/v1/runs/{call_id}")
    async def get_result(call_id: str) -> Any:
        if lookup_result is None:
            return JSONResponse(
                {
                    "call_id": call_id,
                    "status": "not_ready",
                    "error": {"code": "PHONICSMAKER_ENGINE_NOT_BOUND"},
                },
                status_code=503,
            )
        try:
            result = lookup_result(call_id)
        except TimeoutError:
            return JSONResponse({"call_id": call_id, "status": "running"}, status_code=202)
        except Exception:
            return JSONResponse(
                {"call_id": call_id, "status": "failed", "error": {"code": "PHONICSMAKER_RUN_FAILED"}},
                status_code=500,
            )

        try:
            validate_output(result)
        except ValidationError:
            return JSONResponse(
                {
                    "call_id": call_id,
                    "status": "failed",
                    "error": {"code": "PHONICSMAKER_OUTPUT_INVALID"},
                },
                status_code=500,
            )
        return result

    return app
