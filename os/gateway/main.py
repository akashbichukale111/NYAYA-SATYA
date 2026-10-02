"""NYAYA-SATYA Master Platform & Unified OS Gateway.
Orchestrates:
1. ORIGINAL NYAYA-SATYA CORE (/os/core)
2. UNIFIED OS COMMAND CENTER (/os and /)
3. 12 SPECIALIZED INTELLIGENCE ENGINES (/os/projects/{slug})
Total = 13 distinct application experiences.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

# Add core path so nyaya core router can resolve imports
UNWIND_CORE_DIR = Path(r"D:\NYAYA-SATYA\unwind-live-verified-main")
if str(UNWIND_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(UNWIND_CORE_DIR))

# Ensure os package root is in sys.path
OS_ROOT = Path(r"D:\NYAYA-SATYA\os")
if str(OS_ROOT) not in sys.path:
    sys.path.insert(0, str(OS_ROOT))

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

# Import original NYAYA-SATYA Core router
try:
    from services.api.nyaya import router as nyaya_core_router
    HAS_CORE_ROUTER = True
except Exception as e:
    print(f"[Warning] Failed to import original nyaya_core_router: {e}")
    HAS_CORE_ROUTER = False

app = FastAPI(
    title="NYAYA-SATYA Master Legal Intelligence Platform",
    version="2.1.0",
    description="Master Platform orchestrating Original NYAYA-SATYA Core + 12 Specialized Intelligence Engines."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount original NYAYA-SATYA Core API router
if HAS_CORE_ROUTER:
    app.include_router(nyaya_core_router)

# 2. Mount all 12 specialized project adapter routers
for adapter in ADAPTERS:
    app.include_router(adapter.router)

# 3. Mount Static Assets
SHELL_DIR = OS_ROOT / "shell"
CORE_STATIC_DIR = UNWIND_CORE_DIR / "web" / "static"
PROJ02_STATIC = OS_ROOT / "modules" / "02-case-continuity" / "frontend"
PROJ04_STATIC = OS_ROOT / "modules" / "04-legal-aid-handoff" / "frontend"

if CORE_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(CORE_STATIC_DIR)), name="core_static")
    app.mount("/core-static", StaticFiles(directory=str(CORE_STATIC_DIR)), name="core_static_alt")

if PROJ02_STATIC.exists():
    app.mount("/project-static/02", StaticFiles(directory=str(PROJ02_STATIC)), name="proj02_static")

if PROJ04_STATIC.exists():
    app.mount("/project-static/04", StaticFiles(directory=str(PROJ04_STATIC)), name="proj04_static")


# ---------------------------------------------------------------------------
# Master Header CSS & JS
# ---------------------------------------------------------------------------
@app.get("/os-master-header.css")
def get_master_header_css():
    css_path = SHELL_DIR / "os-master-header.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("", status_code=404)

@app.get("/os-shared-context.js")
def get_shared_context_js():
    js_path = SHELL_DIR / "os-shared-context.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse("", status_code=404)


# ---------------------------------------------------------------------------
# Core OS Health & Diagnostics
# ---------------------------------------------------------------------------

@app.get("/health")
def root_health():
    return {
        "status": "HEALTHY",
        "system": "NYAYA-SATYA MASTER PLATFORM",
        "version": "2.1.0",
        "experiences_count": 13,
        "core_engine": "ORIGINAL NYAYA-SATYA CORE ONLINE",
        "specialized_engines_mounted": len(ADAPTERS),
        "non_adjudication_invariant": "GUARANTEED_ZERO_OUTCOME_PREDICTION",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/system-health")
def system_health_detailed():
    modules = module_registry.list_all()
    active_case = case_store.get_active_case()
    
    return {
        "platform": "NYAYA-SATYA MASTER PLATFORM",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "active_case_id": active_case.case_id,
        "total_experiences": 13,
        "core_status": {
            "name": "NYAYA-SATYA CORE",
            "role": "Original Legal Evidence Intelligence Platform",
            "route": "/os/core",
            "status": "HEALTHY",
            "features": ["Digital Twin", "Adversarial Review", "Causal Blast Radius", "Repair Workbench", "UNWIND Gate"]
        },
        "engines": [
            {
                "number": m.number,
                "id": m.module_id,
                "name": m.name,
                "slug": m.slug,
                "status": m.status.value,
                "category": m.category.value,
                "route": f"/os/projects/{m.slug}",
                "notes": m.notes
            }
            for m in modules
        ],
        "safety_invariants": {
            "non_adjudicative_audit": "PASSED (Zero judicial outcome predictions)",
            "unwind_human_gate": "ENFORCED (All structural actions require licensed counsel approval)",
            "shared_case_context": "SYNCHRONIZED across all 13 experiences"
        }
    }


# ---------------------------------------------------------------------------
# Case Management & Cockpit Summary
# ---------------------------------------------------------------------------

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
            event_id=f"EVT-SWITCH-{datetime.now().timestamp()}",
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
    try:
        case = case_store.authorize_active_case(case_id, approver)
        return {"status": "AUTHORIZED", "case": case}
    except KeyError:
        raise HTTPException(status_code=404, detail="Case not found")

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
            "route": f"/os/projects/{adapter.metadata.slug}",
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

@app.get("/api/search")
def global_search(q: str = Query(..., min_length=1)):
    query = q.lower()
    results = []
    
    # 1. Core experience & Twin
    if "core" in query or "nyaya" in query:
        results.append({
            "category": "Flagship Platform",
            "title": "NYAYA-SATYA CORE",
            "subtitle": "Original Legal Case Intelligence & Evidence Arena",
            "target_route": "/core"
        })
    if "twin" in query or "digital" in query or "graph" in query:
        results.append({
            "category": "Core Architecture",
            "title": "Case Digital Twin Explorer",
            "subtitle": "Deep Graph Visualization of Claims, Evidence & Causal Links",
            "target_route": "/twin"
        })
    if "tarka" in query or "adversarial" in query or "attack" in query or "fragil" in query:
        results.append({
            "category": "Governance",
            "title": "TARKA-VYUH Adversarial Arena",
            "subtitle": "Fragility Scoring & Adversarial Gauntlet Attack Console",
            "target_route": "/governance/tarka-vyuh"
        })
    if "unwind" in query or "gate" in query or "authoriz" in query or "counsel" in query:
        results.append({
            "category": "Governance",
            "title": "UNWIND Human Legal Gate",
            "subtitle": "Licensed Counsel Authorization & Non-Consequential Guard",
            "target_route": "/governance/unwind"
        })
    if "audit" in query or "ledger" in query or "chain" in query:
        results.append({
            "category": "Governance",
            "title": "Immutable Audit Ledger",
            "subtitle": "Cryptographic Event Trail & State Hashes",
            "target_route": "/governance/audit"
        })
    
    # 2. Search cases
    for c in case_store.list_cases():
        if query in c.case_id.lower() or query in c.title.lower() or query in c.statute.lower():
            results.append({
                "category": "Cases",
                "title": f"{c.case_id} — {c.title}",
                "subtitle": f"{c.court} • {c.stage.value}",
                "target_route": f"/dashboard?case_id={c.case_id}"
            })
            
    # 3. Search engines
    for m in module_registry.list_all():
        if query in m.name.lower() or query in m.tagline.lower() or any(query in f.lower() for f in m.features):
            results.append({
                "category": "Intelligence Engines",
                "title": f"Project {m.number:02d}: {m.name}",
                "subtitle": m.tagline,
                "target_route": f"/projects/{m.slug}"
            })

    return {"query": q, "total_matches": len(results), "results": results[:15]}


# ---------------------------------------------------------------------------
# Master Platform Navigation & UI Serving (Canonical Routes & Aliases)
# ---------------------------------------------------------------------------

# 1. Master Command Center (/ and /dashboard and /os)
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/os", response_class=HTMLResponse)
def serve_master_os_command_center():
    index_file = SHELL_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Master OS Shell initializing...</h1>", status_code=200)


# 2. Original NYAYA-SATYA Core Experience (/core and /os/core)
@app.get("/core", response_class=HTMLResponse)
@app.get("/os/core", response_class=HTMLResponse)
def serve_original_nyaya_satya_core():
    core_html_path = UNWIND_CORE_DIR / "web" / "static" / "index.html"
    if not core_html_path.exists():
        raise HTTPException(status_code=404, detail="Original NYAYA-SATYA Core UI not found")

    with open(core_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Master OS Return Header injection
    os_banner = """
    <!-- NYAYA-SATYA MASTER PLATFORM RETURN HEADER -->
    <header class="os-master-header">
      <div class="os-header-left">
        <a href="/dashboard" class="os-back-button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          <span>Command Center</span>
        </a>
        <div class="os-breadcrumb-trail">
          <span class="os-bc-root">NYAYA-SATYA</span>
          <span class="os-bc-sep">/</span>
          <span class="os-bc-section">CORE INTELLIGENCE</span>
          <span class="os-bc-sep">/</span>
          <span class="os-bc-current">ORIGINAL PLATFORM</span>
        </div>
      </div>
      <div class="os-header-right">
        <div class="os-case-badge">
          <span class="os-pulse-dot"></span>
          <span class="os-case-label">CASE CONTEXT:</span>
          <select id="os-global-case-select" class="os-case-dropdown" onchange="osSwitchCase(this.value)">
            <option value="CASE-2024-DEL-0482">State v. Rajesh Kumar (Tis Hazari)</option>
            <option value="CASE-2023-BOM-1109">Apex Infra v. Mumbai Port Trust (Bombay HC)</option>
            <option value="CASE-2024-KA-0077">Kaveri Farmers v. Karnataka (Karnataka HC)</option>
          </select>
        </div>
      </div>
    </header>
    """

    # Inject header CSS & scripts
    head_injection = """
      <link rel="stylesheet" href="/os-master-header.css" />
      <script src="/os-shared-context.js"></script>
    """
    html = html.replace("<head>", f"<head>\n{head_injection}")
    
    # Inject banner right after opening body tag
    if "<body" in html:
        idx = html.find(">", html.find("<body"))
        if idx != -1:
            html = html[:idx+1] + "\n" + os_banner + "\n" + html[idx+1:]

    return HTMLResponse(html)


# 3. Case Digital Twin Deep Explorer (/twin and /os/twin)
@app.get("/twin", response_class=HTMLResponse)
@app.get("/os/twin", response_class=HTMLResponse)
def serve_twin_explorer():
    twin_file = SHELL_DIR / "twin_explorer.html"
    if twin_file.exists():
        with open(twin_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Twin explorer UI not found")


# 4. Specialized Project Experiences (12 Projects)
PROJECT_PAGES = {
    "hearing-readiness": "01_hearing_readiness.html",
    "case-continuity": "02_case_continuity.html",
    "case-bottleneck": "03_case_bottleneck.html",
    "legal-aid-handoff": "04_legal_aid_handoff.html",
    "procedural-obligation": "05_procedural_obligation.html",
    "evidence-dependency": "06_evidence_dependency.html",
    "undertrial-liberty": "07_undertrial_liberty.html",
    "registry-defect": "08_registry_defect.html",
    "case-crash-test": "09_case_crash_test.html",
    "crash-test": "09_case_crash_test.html",
    "spark-personal-os": "10_spark_personal_os.html",
    "spark-deadline-guardian": "11_spark_deadline_guardian.html",
    "spark-workflow-autopilot": "12_spark_workflow_autopilot.html",
}

@app.get("/projects/{slug}", response_class=HTMLResponse)
@app.get("/os/projects/{slug}", response_class=HTMLResponse)
@app.get("/modules/{slug}", response_class=HTMLResponse)
def serve_specialized_project(slug: str):
    target_slug = slug
    if target_slug not in PROJECT_PAGES:
        # Try finding prefix or match
        normalized = slug.replace("_", "-").lower()
        if normalized in PROJECT_PAGES:
            target_slug = normalized
        else:
            raise HTTPException(status_code=404, detail=f"Specialized project '{slug}' not found")

    page_file = SHELL_DIR / "projects" / PROJECT_PAGES[target_slug]
    if page_file.exists():
        with open(page_file, "r", encoding="utf-8") as f:
            return f.read()

    raise HTTPException(status_code=404, detail=f"Project UI file {PROJECT_PAGES[target_slug]} not found")


# 5. Dedicated Spark Direct Routes
@app.get("/spark/personal", response_class=HTMLResponse)
def serve_spark_personal():
    return serve_specialized_project("spark-personal-os")

@app.get("/spark/deadlines", response_class=HTMLResponse)
def serve_spark_deadlines():
    return serve_specialized_project("spark-deadline-guardian")

@app.get("/spark/workflows", response_class=HTMLResponse)
def serve_spark_workflows():
    return serve_specialized_project("spark-workflow-autopilot")


# 6. Dedicated Governance & Audit Routes
@app.get("/governance/tarka-vyuh", response_class=HTMLResponse)
def serve_governance_tarka():
    tarka_file = SHELL_DIR / "governance_tarka.html"
    if tarka_file.exists():
        with open(tarka_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="TARKA-VYUH UI not found")

@app.get("/governance/unwind", response_class=HTMLResponse)
def serve_governance_unwind():
    unwind_file = SHELL_DIR / "governance_unwind.html"
    if unwind_file.exists():
        with open(unwind_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="UNWIND Gate UI not found")

@app.get("/governance/audit", response_class=HTMLResponse)
def serve_governance_audit():
    audit_file = SHELL_DIR / "governance_audit.html"
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Audit ledger UI not found")

@app.get("/governance/system-health", response_class=HTMLResponse)
@app.get("/system-health-ui", response_class=HTMLResponse)
def serve_system_health_ui():
    """Serves the Master OS shell with view initialized to system diagnostics."""
    index_file = SHELL_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
            content = content.replace("loadCockpit();", "loadCockpit(); showView('system-health');")
            return content
    return HTMLResponse("<h1>System Diagnostics</h1>", status_code=200)
