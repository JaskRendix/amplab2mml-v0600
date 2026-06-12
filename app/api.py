from importlib.metadata import version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from lxml import etree

from app.builders.b2mml_builder import build_b2mml_xml
from app.cli import model_to_json
from app.csv_export import export_classes_csv, export_equipment_csv
from app.diff import diff_models
from app.excel_export import export_to_excel
from app.html_report import export_to_html
from app.logging_setup import (
    log_invalid_xml,
    logger,
    request_id_middleware,
    request_logging_middleware,
)
from app.pipeline import InvalidXML, run_pipeline_from_bytes
from app.schemas import DiffResponse, HealthResponse, ModelResponse, StatsResponse
from app.stats import compute_stats
from app.validators import validate_model

PIPELINE_VERSION = version("ampla-b2mml-v0600")


def load_schema():
    base = Path(__file__).resolve().parent.parent / "schemas"
    equipment_xsd = base / "B2MML-V0600-Equipment.xsd"

    parser = etree.XMLParser(load_dtd=False, resolve_entities=False)
    schema_doc = etree.parse(str(equipment_xsd), parser)
    return etree.XMLSchema(schema_doc)


app = FastAPI(
    title="Ampla → B2MML V0600 API",
    description="Strict transformer for converting Ampla Project XML into ISA‑95 B2MML V0600 Equipment models.",
    version="1.0.0",
)

app.middleware("http")(request_id_middleware)
app.middleware("http")(request_logging_middleware)


async def load_model(
    file: UploadFile, request: Request, endpoint: str
) -> dict[str, Any]:
    if file is None:
        raise HTTPException(status_code=400, detail="Missing file upload")

    try:
        return run_pipeline_from_bytes(await file.read())
    except InvalidXML:
        log_invalid_xml(endpoint, request)
        raise HTTPException(status_code=400, detail="Invalid XML")


def binary_response(data: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> dict[str, str]:
    try:
        run_pipeline_from_bytes(b"<Ampla></Ampla>")
        return {"status": "ok", "pipeline": "ready"}
    except Exception:
        logger.error("Health check failed")
        return {"status": "error", "pipeline": "failed"}


@app.get("/info", tags=["system"])
def info() -> dict[str, str]:
    return {
        "api_version": app.version,
        "pipeline_version": PIPELINE_VERSION,
        "commit": "unknown",
    }


@app.post(
    "/convert/json",
    response_model=ModelResponse,
    tags=["convert"],
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "example": {
                        "file": {
                            "filename": "sample.xml",
                            "contentType": "application/xml",
                        }
                    }
                }
            }
        }
    },
)
async def convert_json(file: UploadFile, request: Request) -> dict[str, Any]:
    model = await load_model(file, request, "/convert/json")

    # model_to_json already returns:
    # { "equipment": [...], "classes": [...], "warnings": [...] }
    return model_to_json(model)


@app.post(
    "/convert/xml",
    tags=["convert"],
    responses={200: {"content": {"application/xml": {}}}},
)
async def convert_xml(file: UploadFile, request: Request) -> Response:
    model = await load_model(file, request, "/convert/xml")

    # IMPORTANT: v0600 builder requires config
    xml = build_b2mml_xml(model, config=model.get("config", {}))

    return Response(content=xml, media_type="application/xml")


@app.post("/diff/json", response_model=DiffResponse, tags=["diff"])
async def diff_json(file_a: UploadFile, file_b: UploadFile, request: Request):
    model_a = await load_model(file_a, request, "/diff/json")
    model_b = await load_model(file_b, request, "/diff/json")
    return diff_models(model_a, model_b).to_dict()


@app.post("/diff/text", tags=["diff"], responses={200: {"content": {"text/plain": {}}}})
async def diff_text(
    file_a: UploadFile, file_b: UploadFile, request: Request
) -> Response:
    model_a = await load_model(file_a, request, "/diff/text")
    model_b = await load_model(file_b, request, "/diff/text")
    return Response(
        content=diff_models(model_a, model_b).to_text(), media_type="text/plain"
    )


@app.post("/convert/excel", tags=["convert"])
async def convert_excel(file: UploadFile, request: Request) -> Response:
    model = await load_model(file, request, "/convert/excel")
    data = export_to_excel(model)
    return binary_response(
        data,
        "equipment.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/convert/csv/equipment", tags=["convert"])
async def convert_csv_equipment(file: UploadFile, request: Request) -> Response:
    model = await load_model(file, request, "/convert/csv/equipment")
    return binary_response(export_equipment_csv(model), "equipment.csv", "text/csv")


@app.post("/convert/csv/classes", tags=["convert"])
async def convert_csv_classes(file: UploadFile, request: Request) -> Response:
    model = await load_model(file, request, "/convert/csv/classes")
    return binary_response(export_classes_csv(model), "classes.csv", "text/csv")


@app.post("/stats", response_model=StatsResponse, tags=["stats"])
async def stats(file: UploadFile, request: Request):
    model = await load_model(file, request, "/stats")
    stats_dict = compute_stats(model).to_dict()
    stats_dict["warnings"] = model.get("warnings", [])
    return stats_dict


@app.post("/convert/html", tags=["convert"])
async def convert_html(file: UploadFile, request: Request) -> Response:
    model = await load_model(file, request, "/convert/html")
    return Response(
        content=export_to_html(model), media_type="text/html; charset=utf-8"
    )


@app.post("/validate", tags=["validate"])
async def validate(file: UploadFile, request: Request) -> dict[str, Any]:
    model = await load_model(file, request, "/validate")

    # model["warnings"] already contains transformer + validator warnings
    all_warnings = model.get("warnings", [])

    # ERROR warnings invalidate the model
    has_errors = any(w.startswith("ERROR:") for w in all_warnings)

    return {"warnings": all_warnings, "valid": not has_errors}


@app.post("/validate/schema", tags=["validate"])
async def validate_schema(file: UploadFile, request: Request):
    model = await load_model(file, request, "/validate/schema")
    xml = build_b2mml_xml(model, config=model.get("config", {}))
    doc = etree.fromstring(xml.encode())

    schema = load_schema()
    valid = schema.validate(doc)

    return {"valid": valid, "errors": str(schema.error_log)}
