from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import json
import os
import asyncio
from datetime import datetime

app = FastAPI(title="MetaBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───────────────────────────────────────────────────────────────────
OM_HOST = os.getenv("OPENMETADATA_HOST", "http://localhost:8585")
OM_TOKEN = os.getenv("OPENMETADATA_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

OM_HEADERS = {
    "Authorization": f"Bearer {OM_TOKEN}",
    "Content-Type": "application/json",
}

# ─── Models ───────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    om_host: Optional[str] = None
    om_token: Optional[str] = None

class LineageRequest(BaseModel):
    entity_type: str
    fqn: str
    om_host: Optional[str] = None
    om_token: Optional[str] = None

class ClassifyRequest(BaseModel):
    table_fqn: str
    om_host: Optional[str] = None
    om_token: Optional[str] = None

class ScanRequest(BaseModel):
    om_host: Optional[str] = None
    om_token: Optional[str] = None

# ─── OpenMetadata helpers ──────────────────────────────────────────────────────

async def om_get(path: str, host: str = None, token: str = None):
    base = host or OM_HOST
    tok = token or OM_TOKEN
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"} if tok else {"Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{base}/api/v1{path}", headers=headers)
        r.raise_for_status()
        return r.json()

async def om_patch(path: str, body: dict, host: str = None, token: str = None):
    base = host or OM_HOST
    tok = token or OM_TOKEN
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json-patch+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.patch(f"{base}/api/v1{path}", headers=headers, json=body)
        r.raise_for_status()
        return r.json()

async def om_put(path: str, body: dict, host: str = None, token: str = None):
    base = host or OM_HOST
    tok = token or OM_TOKEN
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{base}/api/v1{path}", headers=headers, json=body)
        r.raise_for_status()
        return r.json()

# ─── PII detection logic ───────────────────────────────────────────────────────
PII_PATTERNS = {
    "email": ["email", "mail", "e_mail", "emailaddress", "user_email", "contact_email"],
    "phone": ["phone", "mobile", "cell", "telephone", "phonenumber", "phone_number", "contact_number"],
    "ssn": ["ssn", "social_security", "socialsecurity", "tax_id", "taxid"],
    "credit_card": ["credit_card", "creditcard", "card_number", "cardnumber", "cc_number"],
    "date_of_birth": ["dob", "date_of_birth", "dateofbirth", "birth_date", "birthdate"],
    "address": ["address", "street", "zipcode", "zip_code", "postal_code", "postalcode"],
    "name": ["first_name", "last_name", "fullname", "full_name", "firstname", "lastname", "customer_name"],
    "ip_address": ["ip_address", "ip_addr", "ipaddress", "client_ip"],
    "passport": ["passport", "passport_number", "passportno"],
    "national_id": ["national_id", "nationalid", "id_number", "idnumber", "aadhaar", "pan_number"],
}

def detect_pii_columns(columns: list) -> list:
    flagged = []
    for col in columns:
        col_name = col.get("name", "").lower().replace(" ", "_")
        for pii_type, patterns in PII_PATTERNS.items():
            if any(p in col_name for p in patterns):
                flagged.append({
                    "column": col.get("name"),
                    "pii_type": pii_type,
                    "dataType": col.get("dataType", "unknown"),
                })
                break
    return flagged

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/om/test")
async def test_om_connection(req: ScanRequest):
    try:
        data = await om_get("/tables?limit=1", req.om_host, req.om_token)
        return {"connected": True, "message": "OpenMetadata connected successfully"}
    except Exception as e:
        return {"connected": False, "message": str(e)}

@app.get("/api/om/stats")
async def get_stats(om_host: str = None, om_token: str = None):
    try:
        tables = await om_get("/tables?limit=1", om_host, om_token)
        topics = await om_get("/topics?limit=1", om_host, om_token)
        dashboards = await om_get("/dashboards?limit=1", om_host, om_token)
        pipelines = await om_get("/pipelines?limit=1", om_host, om_token)
        return {
            "tables": tables.get("paging", {}).get("total", 0),
            "topics": topics.get("paging", {}).get("total", 0),
            "dashboards": dashboards.get("paging", {}).get("total", 0),
            "pipelines": pipelines.get("paging", {}).get("total", 0),
        }
    except Exception as e:
        return {"tables": 0, "topics": 0, "dashboards": 0, "pipelines": 0, "error": str(e)}

@app.get("/api/om/search")
async def search_entities(q: str, entity_type: str = "", limit: int = 10, om_host: str = None, om_token: str = None):
    try:
        index = {
            "table": "table_search_index",
            "dashboard": "dashboard_search_index",
            "pipeline": "pipeline_search_index",
            "topic": "topic_search_index",
        }.get(entity_type, "all")
        path = f"/search/query?q={q}&index={index}&from=0&size={limit}"
        data = await om_get(path, om_host, om_token)
        hits = data.get("hits", {}).get("hits", [])
        results = []
        for h in hits:
            src = h.get("_source", {})
            results.append({
                "id": src.get("id"),
                "name": src.get("name"),
                "fullyQualifiedName": src.get("fullyQualifiedName"),
                "description": src.get("description", ""),
                "entityType": src.get("entityType", entity_type),
                "owners": [o.get("displayName", o.get("name", "")) for o in src.get("owners", [])],
                "tags": [t.get("tagFQN", "") for t in src.get("tags", [])],
                "tier": next((t.get("tagFQN", "") for t in src.get("tags", []) if "Tier" in t.get("tagFQN", "")), ""),
            })
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/om/lineage")
async def get_lineage(req: LineageRequest):
    try:
        path = f"/lineage/{req.entity_type}/name/{req.fqn}?upstreamDepth=3&downstreamDepth=3"
        data = await om_get(path, req.om_host, req.om_token)
        nodes = data.get("nodes", [])
        edges = data.get("downstreamEdges", []) + data.get("upstreamEdges", [])
        return {
            "entity": data.get("entity", {}),
            "nodes": nodes,
            "edges": edges,
            "upstream_count": len(data.get("upstreamEdges", [])),
            "downstream_count": len(data.get("downstreamEdges", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/om/classify")
async def classify_table(req: ClassifyRequest):
    try:
        # Fetch table columns
        path = f"/tables/name/{req.table_fqn}?fields=columns,tags,owners"
        table = await om_get(path, req.om_host, req.om_token)
        columns = table.get("columns", [])
        pii_cols = detect_pii_columns(columns)

        applied = []
        for col_info in pii_cols:
            try:
                patch = [{
                    "op": "add",
                    "path": "/tags/-",
                    "value": {
                        "tagFQN": f"PII.{col_info['pii_type'].replace('_', ' ').title().replace(' ', '')}",
                        "source": "Classification",
                        "labelType": "Automated",
                        "state": "Suggested"
                    }
                }]
                await om_patch(f"/tables/{table['id']}/columns/{col_info['column']}", patch, req.om_host, req.om_token)
                applied.append(col_info)
            except:
                applied.append({**col_info, "tag_applied": False})

        return {
            "table": req.table_fqn,
            "total_columns": len(columns),
            "pii_detected": pii_cols,
            "classified": len(pii_cols),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/om/scan-all-pii")
async def scan_all_pii(req: ScanRequest):
    try:
        tables_data = await om_get("/tables?limit=50&fields=columns,tags", req.om_host, req.om_token)
        tables = tables_data.get("data", [])
        report = []
        total_pii = 0
        for table in tables:
            cols = table.get("columns", [])
            pii = detect_pii_columns(cols)
            if pii:
                report.append({
                    "table": table.get("fullyQualifiedName"),
                    "pii_columns": pii,
                    "risk_level": "HIGH" if len(pii) >= 3 else "MEDIUM" if len(pii) >= 1 else "LOW",
                })
                total_pii += len(pii)
        return {
            "tables_scanned": len(tables),
            "tables_with_pii": len(report),
            "total_pii_columns": total_pii,
            "report": sorted(report, key=lambda x: len(x["pii_columns"]), reverse=True),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/om/data-quality")
async def get_data_quality(om_host: str = None, om_token: str = None):
    try:
        test_data = await om_get("/dataQuality/testCases?limit=50&fields=testCaseResult", om_host, om_token)
        tests = test_data.get("data", [])
        passed = sum(1 for t in tests if t.get("testCaseResult", {}).get("testCaseStatus") == "Success")
        failed = sum(1 for t in tests if t.get("testCaseResult", {}).get("testCaseStatus") == "Failed")
        aborted = sum(1 for t in tests if t.get("testCaseResult", {}).get("testCaseStatus") == "Aborted")
        return {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "aborted": aborted,
            "pass_rate": round((passed / len(tests) * 100), 1) if tests else 0,
            "failing_tests": [
                {
                    "name": t.get("name"),
                    "entity": t.get("entityLink", "").split("::")[-1].strip(">"),
                    "status": t.get("testCaseResult", {}).get("testCaseStatus"),
                }
                for t in tests if t.get("testCaseResult", {}).get("testCaseStatus") in ["Failed", "Aborted"]
            ][:10],
        }
    except Exception as e:
        return {"total": 0, "passed": 0, "failed": 0, "aborted": 0, "pass_rate": 0, "failing_tests": [], "error": str(e)}

@app.get("/api/om/recent-activity")
async def get_recent_activity(om_host: str = None, om_token: str = None):
    try:
        data = await om_get("/feeds?limit=20", om_host, om_token)
        feeds = data.get("data", [])
        activities = []
        for f in feeds[:10]:
            activities.append({
                "type": f.get("feedType", "Conversation"),
                "message": f.get("message", ""),
                "created_by": f.get("createdBy", ""),
                "updated_at": f.get("updatedAt", ""),
                "entity": f.get("about", "").split("::")[-1].strip(">") if f.get("about") else "",
            })
        return {"activities": activities}
    except Exception as e:
        return {"activities": [], "error": str(e)}

# ─── AI Chat with tools ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are MetaBot, an intelligent AI assistant for OpenMetadata — the open-source unified metadata platform.

You help data engineers, analysts, and governance teams:
- Discover and search data assets (tables, dashboards, pipelines, topics)
- Understand data lineage and impact analysis
- Detect and classify PII (Personally Identifiable Information)
- Monitor data quality and observability
- Manage governance, ownership, and tagging
- Navigate the OpenMetadata platform

You have access to real OpenMetadata APIs. When users ask about their data, you can:
1. Search for tables, dashboards, pipelines
2. Get data lineage (upstream/downstream)
3. Detect PII columns in tables
4. Check data quality test results
5. View recent platform activity

Always be helpful, concise, and data-focused. Format results clearly with markdown.
When you don't have access to OpenMetadata (no connection), explain what the user would see and guide them to connect.

For PII detection, explain the risk and recommended actions.
For lineage, explain the impact in business terms.
For data quality, prioritize the most critical failures.

Be conversational but professional. You're a trusted data advisor."""

TOOLS_DESCRIPTION = """
Available OpenMetadata capabilities:
- search_entities(query, entity_type) - Search tables, dashboards, pipelines, topics
- get_lineage(entity_type, fqn) - Get upstream/downstream lineage  
- classify_pii(table_fqn) - Detect and tag PII columns
- scan_all_pii() - Scan all tables for PII risk
- get_data_quality() - Check data quality test results
- get_stats() - Platform-wide statistics
"""

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        import anthropic as ac
        client = ac.Anthropic(api_key=ANTHROPIC_KEY)

        # Build context from OM if possible
        om_context = ""
        try:
            stats = await get_stats(req.om_host, req.om_token)
            om_context = f"\nCurrent OpenMetadata stats: {json.dumps(stats)}"
        except:
            om_context = "\nNote: OpenMetadata connection not available. Providing guidance based on the platform's capabilities."

        messages = []
        for m in req.history[-10:]:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": req.message})

        def generate():
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=SYSTEM_PROMPT + om_context + TOOLS_DESCRIPTION,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/action")
async def chat_action(req: ChatRequest):
    """Handle structured action requests from chat"""
    msg = req.message.lower()
    result = {}

    try:
        if "pii" in msg and ("scan" in msg or "all" in msg or "detect" in msg):
            result = await scan_all_pii(ScanRequest(om_host=req.om_host, om_token=req.om_token))
            result["action"] = "pii_scan"

        elif "quality" in msg or "test" in msg or "dq" in msg:
            result = await get_data_quality(req.om_host, req.om_token)
            result["action"] = "data_quality"

        elif "stats" in msg or "overview" in msg or "summary" in msg:
            result = await get_stats(req.om_host, req.om_token)
            result["action"] = "stats"

        elif "activity" in msg or "recent" in msg:
            result = await get_recent_activity(req.om_host, req.om_token)
            result["action"] = "activity"

        elif "search" in msg or "find" in msg or "show" in msg:
            query = req.message.split("search")[-1].split("find")[-1].split("show")[-1].strip()
            result = await search_entities(query, om_host=req.om_host, om_token=req.om_token)
            result["action"] = "search"

        return result

    except Exception as e:
        return {"error": str(e), "action": "error"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
