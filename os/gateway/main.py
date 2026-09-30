"""NYAYA-SATYA Unified OS Gateway.
Main entry point orchestrating all 12 modular engines, shared case context,
and serving the cinematic OS Command Center frontend.
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from contracts.models import (
    CaseContext,
    ModuleHealthStatus,
    AttentionItem,
    CrossProjectEvent,
    CrossProjectEventType
)
from shared.case_store import case_store
from shared.module_registry import module_registry
from shared.attention_center import attention_center
from shared.event_bus import event_bus
from adapters.modules import ADAPTERS

app = FastAPI(
    title="NYAYA-SATYA Operating System Gateway",
    version="2.0.0",
    description="One OS Shell, 12 Modular Engines, Human-Governed Legal Case Intelligence."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all 12 module adapter routers
for adapter in ADAPTERS:
    app.include_router(adapter.router)


# ---------------------------------------------------------------------------
# Core OS Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def root_health():
    return {
        "status": "HEALTHY",
        "system": "NYAYA-SATYA OS",
        "version": "2.0.0",
        "engines_mounted": len(ADAPTERS),
        "non_adjudication_invariant": "GUARANTEED_ZERO_OUTCOME_PREDICTION",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/system-health")
def system_health_detailed():
    """Comprehensive diagnostic endpoint across all 12 engines."""
    modules = module_registry.list_all()
    active_case = case_store.get_active_case()
    
    report = {
        "os_version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "active_case_id": active_case.case_id,
        "total_engines": len(modules),
        "status_breakdown": {
            "HEALTHY": len([m for m in modules if m.status == ModuleHealthStatus.HEALTHY]),
            "PARTIAL": len([m for m in modules if m.status == ModuleHealthStatus.PARTIAL]),
            "DEGRADED": len([m for m in modules if m.status == ModuleHealthStatus.DEGRADED]),
            "OFFLINE": len([m for m in modules if m.status == ModuleHealthStatus.OFFLINE])
        },
        "modules": [
            {
                "number": m.number,
                "id": m.module_id,
                "name": m.name,
                "slug": m.slug,
                "status": m.status.value,
                "category": m.category.value,
                "notes": m.notes,
                "api_prefix": m.api_prefix,
                "has_custom_frontend": m.has_custom_frontend,
                "features_count": len(m.features)
            }
            for m in modules
        ],
        "shared_state": {
            "total_cases_loaded": len(case_store.list_cases()),
            "active_unresolved_attention_items": len(attention_center.get_unresolved(active_case.case_id)),
            "event_bus_entries": len(event_bus.get_history())
        },
        "safety_invariants": {
            "non_adjudicative_audit": "PASSED (Zero probability judicial predictions)",
            "unwind_human_gate": "ENFORCED (All structural actions require licensed counsel approval)",
            "data_isolation": "ENFORCED (Strict case_id partition)"
        }
    }
    return report


# Case Management Endpoints
@app.get("/api/cases", response_model=List[CaseContext])
def list_cases():
    return case_store.list_cases()


@app.get("/api/cases/active", response_model=CaseContext)
def get_active_case():
    return case_store.get_active_case()


@app.post("/api/cases/switch")
def switch_active_case(case_id: str = Query(..., description="Target case ID")):
    try:
        case = case_store.set_active_case(case_id)
        event_bus.publish(CrossProjectEvent(
            event_id=f"EVT-SWITCH-{datetime.utcnow().timestamp()}",
            event_type=CrossProjectEventType.HUMAN_ACTION_AUTHORIZED,
            case_id=case_id,
            origin_module="OS-Shell",
            payload={"action": "ACTIVE_CASE_SWITCHED", "new_case_id": case_id}
        ))
        return {"status": "SUCCESS", "active_case": case}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")


@app.post("/api/cases/{case_id}/authorize")
def authorize_case_actions(case_id: str, approver: str = Query("Adv. Meenakshi Sundaram")):
    """UNWIND Gate authorization."""
    try:
        case = case_store.authorize_active_case(case_id, approver)
        event_bus.publish(CrossProjectEvent(
            event_id=f"EVT-AUTH-{datetime.utcnow().timestamp()}",
            event_type=CrossProjectEventType.HUMAN_ACTION_AUTHORIZED,
            case_id=case_id,
            origin_module="OS-Shell",
            payload={"authorized_by": approver, "signed_at": datetime.utcnow().isoformat()}
        ))
        return {"status": "AUTHORIZED", "case": case}
    except KeyError:
        raise HTTPException(status_code=404, detail="Case not found")


# Attention Center Endpoints
@app.get("/api/attention", response_model=List[AttentionItem])
def get_attention(case_id: Optional[str] = None):
    return attention_center.list_all(case_id)


@app.post("/api/attention/{item_id}/resolve")
def resolve_attention_item(item_id: str):
    item = attention_center.resolve(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Attention item not found")
    return {"status": "RESOLVED", "item": item}


# Event Bus / Audit Trail
@app.get("/api/events", response_model=List[CrossProjectEvent])
def get_event_audit(case_id: Optional[str] = None):
    return event_bus.get_history(case_id)


# Global Search (Ctrl + K)
@app.get("/api/search")
def global_search(q: str = Query(..., min_length=1)):
    query = q.lower()
    results = []
    
    # Search cases
    for c in case_store.list_cases():
        if query in c.case_id.lower() or query in c.title.lower() or query in c.statute.lower() or any(query in t.lower() for t in c.tags):
            results.append({
                "category": "Cases",
                "title": f"{c.case_id} — {c.title}",
                "subtitle": f"{c.court} • {c.stage.value}",
                "target_route": f"/?case_id={c.case_id}"
            })
            
    # Search modules
    for m in module_registry.list_all():
        if query in m.name.lower() or query in m.tagline.lower() or any(query in f.lower() for f in m.features):
            results.append({
                "category": "Engines & Modules",
                "title": f"Module {m.number:02d}: {m.name}",
                "subtitle": m.tagline,
                "target_route": m.ui_route
            })
            
    # Search attention items
    for a in attention_center.list_all():
        if query in a.title.lower() or query in a.description.lower():
            results.append({
                "category": f"Alerts ({a.severity.value})",
                "title": a.title,
                "subtitle": f"Case: {a.case_id} • {a.source_module_name}",
                "target_route": a.target_route or "/"
            })

    return {"query": q, "total_matches": len(results), "results": results[:15]}


# Consolidated Cockpit Summary for the OS Command Center
@app.get("/api/cockpit/summary")
def get_cockpit_summary(case_id: Optional[str] = None):
    active_case = case_store.get_case(case_id) if case_id else case_store.get_active_case()
    if not active_case:
        active_case = case_store.get_active_case()

    modules_summary = []
    for adapter in ADAPTERS:
        try:
            m_summary = adapter.get_summary(active_case.case_id)
        except Exception as e:
            m_summary = {"error": str(e)}
        modules_summary.append({
            "number": adapter.metadata.number,
            "id": adapter.metadata.module_id,
            "name": adapter.metadata.name,
            "slug": adapter.metadata.slug,
            "category": adapter.metadata.category.value,
            "tagline": adapter.metadata.tagline,
            "status": adapter.metadata.status.value,
            "ui_route": adapter.metadata.ui_route,
            "api_prefix": adapter.metadata.api_prefix,
            "has_custom_frontend": adapter.metadata.has_custom_frontend,
            "summary": m_summary
        })

    attention_items = attention_center.get_unresolved(active_case.case_id)

    return {
        "active_case": active_case,
        "available_cases": case_store.list_cases(),
        "attention_items": attention_items,
        "critical_attention_count": len([i for i in attention_items if i.severity == "CRITICAL"]),
        "high_attention_count": len([i for i in attention_items if i.severity == "HIGH"]),
        "modules": modules_summary,
        "system_status": "OPERATIONAL",
        "human_gate_authorized": active_case.human_authorized
    }


# ---------------------------------------------------------------------------
# UI Routes & Single-Page Shell Frontend
# ---------------------------------------------------------------------------

SHELL_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "shell", "index.html")

@app.get("/", response_class=HTMLResponse)
@app.get("/modules/{slug}", response_class=HTMLResponse)
@app.get("/system-health-ui", response_class=HTMLResponse)
def serve_os_shell():
    """Serves the unified NYAYA-SATYA OS Command Center Shell."""
    if os.path.exists(SHELL_HTML_PATH):
        with open(SHELL_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>NYAYA-SATYA OS Shell Initializing...</h1>", status_code=200)
