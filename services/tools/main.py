"""
Odus Tools API — Ferramentas de browser, intake, verify e memory.

Endpoints:
  POST /browser/navigate    — navega pra URL, retorna screenshot + console errors
  POST /browser/measure     — mede computed styles de elementos
  POST /browser/screenshot  — tira screenshot de uma URL
  POST /intake/extract      — extrai tokens do Figma (REST API)
  POST /verify/geometry     — compara contrato com browser real
  POST /memory/search       — busca memórias relevantes
  POST /memory/add          — adiciona memória
  GET  /health              — health check
"""
import json
import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Odus Tools API starting...")
    yield
    # Shutdown
    print("Odus Tools API stopping...")

app = FastAPI(
    title="Odus Tools API",
    description="Browser, Intake, Verify, Memory tools for Multica agents",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Models ──

class NavigateRequest(BaseModel):
    url: str
    wait_ms: int = 3000

class MeasureRequest(BaseModel):
    url: str
    selector: str
    properties: list[str]
    wait_ms: int = 3000

class MeasureAllRequest(BaseModel):
    url: str
    selector: str
    properties: list[str]
    wait_ms: int = 3000

class ScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True
    wait_ms: int = 3000

class IntakeRequest(BaseModel):
    file_key: str
    node_id: str

class VerifyRequest(BaseModel):
    url: str
    contract: dict
    wait_ms: int = 5000

class MemorySearchRequest(BaseModel):
    query: str
    client: str = ""
    stack: str = ""
    task_type: str = ""
    limit: int = 5

class MemoryAddRequest(BaseModel):
    content: str
    client: str = ""
    stack: str = ""
    task_type: str = ""
    source: str = "api"


# ── Health ──

@app.get("/health")
def health():
    return {"status": "ok", "service": "odus-tools"}


# ── Browser endpoints ──

@app.post("/browser/navigate")
def browser_navigate(req: NavigateRequest):
    from browser import OdusBrowser
    with OdusBrowser() as b:
        result = b.navigate(req.url, wait_ms=req.wait_ms)
        metrics = b.get_page_metrics()
        return {
            "url": result.url,
            "status": result.status,
            "console_errors": result.console_errors,
            "console_warnings": result.console_warnings,
            "network_errors": result.network_errors,
            "load_time_ms": result.load_time_ms,
            "has_errors": result.has_errors,
            "metrics": metrics,
        }


@app.post("/browser/measure")
def browser_measure(req: MeasureRequest):
    from browser import OdusBrowser
    with OdusBrowser() as b:
        b.navigate(req.url, wait_ms=req.wait_ms)
        result = b.measure_element(req.selector, req.properties)
        if result is None:
            raise HTTPException(404, f"Element not found: {req.selector}")
        return {"selector": req.selector, "styles": result}


@app.post("/browser/measure-all")
def browser_measure_all(req: MeasureAllRequest):
    from browser import OdusBrowser
    with OdusBrowser() as b:
        b.navigate(req.url, wait_ms=req.wait_ms)
        results = b.measure_all(req.selector, req.properties)
        return {"selector": req.selector, "count": len(results), "elements": results}


@app.post("/browser/screenshot")
def browser_screenshot(req: ScreenshotRequest):
    from browser import OdusBrowser
    tmp = tempfile.mktemp(suffix=".png", prefix="odus-screenshot-")
    with OdusBrowser() as b:
        b.navigate(req.url, wait_ms=req.wait_ms)
        path = b.screenshot(tmp, full_page=req.full_page)
        if not path:
            raise HTTPException(500, "Failed to take screenshot")
        return FileResponse(path, media_type="image/png", filename="screenshot.png")


# ── Intake endpoints ──

@app.post("/intake/extract")
def intake_extract(req: IntakeRequest):
    from intake import DesignIntake
    intake = DesignIntake()
    contract = intake.extract(req.file_key, req.node_id)
    return contract


# ── Verify endpoints ──

@app.post("/verify/geometry")
def verify_geometry(req: VerifyRequest):
    from verify_geometry import GeometryVerifier
    verifier = GeometryVerifier()
    result = verifier.verify(req.url, req.contract, wait_ms=req.wait_ms)
    return {
        "url": result.url,
        "total_checks": result.total_checks,
        "passed": result.passed,
        "failed": result.failed,
        "pass_rate": result.pass_rate,
        "is_passing": result.is_passing,
        "diffs": result.to_dict().get("diffs", []),
        "prompt": result.to_prompt(),
    }


# ── Memory endpoints ──

@app.post("/memory/search")
def memory_search(req: MemorySearchRequest):
    from memory import OdusMemory
    mem = OdusMemory()
    if not mem.available:
        return {"available": False, "results": [], "message": "Mem0 not configured (needs LLM API key)"}
    results = mem.search(
        req.query, client=req.client, stack=req.stack,
        task_type=req.task_type, limit=req.limit,
    )
    return {"available": True, "results": results}


@app.post("/memory/add")
def memory_add(req: MemoryAddRequest):
    from memory import OdusMemory
    mem = OdusMemory()
    if not mem.available:
        return {"available": False, "id": None, "message": "Mem0 not configured"}
    mid = mem.add(
        req.content, client=req.client, stack=req.stack,
        task_type=req.task_type, source=req.source,
    )
    return {"available": True, "id": mid}


@app.post("/memory/context")
def memory_context(req: MemorySearchRequest):
    from memory import OdusMemory
    mem = OdusMemory()
    if not mem.available:
        return {"available": False, "context": ""}
    ctx = mem.build_context(
        client=req.client, stack=req.stack,
        task_type=req.task_type, task_title=req.query,
        limit=req.limit,
    )
    return {"available": True, "context": ctx}
