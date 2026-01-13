from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .api import generate_quote_from_files

app = FastAPI(title="SLA Quote Server", version="0.1.0")

DEFAULT_CONFIG = "config/default.example.yaml"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTS = {".sldprt", ".igs", ".iges", ".x_t", ".step", ".stp", ".stl", ".json", ".yaml", ".yml"}


def _safe_ext(name: str) -> str:
    return Path(name).suffix.lower()


async def _read_upload_limited(upload: UploadFile, max_bytes: int = MAX_BYTES) -> bytes:
    data = await upload.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large: {len(data)/1024/1024:.2f} MB. Max is 10 MB.")
    return data


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/quote")
async def quote(
    # Either input_json string OR input_file upload
    input_json: Optional[str] = Form(default=None),
    input_file: Optional[UploadFile] = File(default=None),

    # Optional CAD upload
    cad_file: Optional[UploadFile] = File(default=None),

    # Config selection: default to example config
    config_name: str = Form(default=DEFAULT_CONFIG),

    # Output directory (relative or absolute). For local dev, dist is fine.
    out_dir: str = Form(default="dist"),
):
    if (input_json is None) and (input_file is None):
        raise HTTPException(status_code=400, detail="Provide either input_json (string) or input_file (upload).")
    if (input_json is not None) and (input_file is not None):
        raise HTTPException(status_code=400, detail="Provide only one of input_json or input_file, not both.")

    cfg_path = Path(config_name)
    if not cfg_path.exists():
        raise HTTPException(status_code=400, detail=f"Config not found: {cfg_path}")

    # Prepare a temp workspace for uploaded files
    with tempfile.TemporaryDirectory(prefix="sla_quote_") as td:
        td_path = Path(td)

        # Write input JSON
        input_json_path = td_path / "input.json"
        if input_json is not None:
            try:
                parsed = json.loads(input_json)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"input_json is invalid JSON: {e}") from e
            input_json_path.write_text(json.dumps(parsed), encoding="utf-8")
        else:
            assert input_file is not None
            if _safe_ext(input_file.filename or "") != ".json":
                raise HTTPException(status_code=400, detail="input_file must be a .json file.")
            data = await _read_upload_limited(input_file)
            input_json_path.write_bytes(data)

        # Optional CAD file
        cad_path: Optional[Path] = None
        if cad_file is not None:
            ext = _safe_ext(cad_file.filename or "")
            if ext not in ALLOWED_EXTS:
                raise HTTPException(status_code=400, detail=f"Unsupported CAD extension: {ext}")
            # Enforce 10MB for CAD file too
            cad_bytes = await _read_upload_limited(cad_file)
            cad_path = td_path / f"cad{ext}"
            cad_path.write_bytes(cad_bytes)

        # Run quote generation (writes artifacts to out_dir)
        try:
            result = generate_quote_from_files(
                input_json_path=input_json_path,
                config_path=cfg_path,
                cad_file_path=cad_path if cad_path else None,
                out_dir=out_dir,
            )
        except NotImplementedError as e:
            # Non-STL CAD types are accepted but not automated (yet)
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Quote generation failed: {e}") from e

        artifacts = {
            "pdf": result.get("artifact_pdf"),
            "xlsx": result.get("artifact_xlsx"),
            "json": result.get("artifact_json"),
        }

        return JSONResponse({"quote": result, "artifacts": artifacts})
