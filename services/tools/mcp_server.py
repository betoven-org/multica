"""
Odus Tools MCP Server — expõe browser, intake, verify, memory e skill como MCP tools.

Roda como stdio MCP server. O daemon do Multica conecta e expõe as tools pros agents.

Tools disponíveis:
  browser_navigate     — navega pra URL, retorna status + console errors
  browser_screenshot   — tira screenshot de uma URL
  browser_measure      — mede computed styles de um elemento
  browser_measure_all  — mede computed styles de todos os elementos que batem
  intake_extract       — extrai design tokens do Figma
  verify_geometry      — compara contrato com browser real
  memory_search        — busca memórias relevantes
  memory_add           — adiciona memória
  skill_search         — busca skills disponíveis no workspace por query
  skill_read           — lê conteúdo completo de uma skill pelo nome
"""
import json
import os
import sys
import tempfile
from pathlib import Path


def read_message():
    """Lê uma mensagem JSON-RPC do stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    # MCP usa Content-Length header + JSON body
    if line.startswith("Content-Length:"):
        length = int(line.split(":")[1].strip())
        sys.stdin.readline()  # empty line
        body = sys.stdin.read(length)
        return json.loads(body)
    # Ou JSON direto (fallback)
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def send_message(msg):
    """Envia mensagem JSON-RPC pro stdout."""
    body = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
    sys.stdout.flush()


def send_result(id, result):
    send_message({"jsonrpc": "2.0", "id": id, "result": result})


def send_error(id, code, message):
    send_message({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})


# ── Tool definitions ──

TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL and return page status, console errors, network errors, and load time. Use to check if a page loads correctly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "wait_ms": {"type": "integer", "description": "Wait time in ms after load (default 3000)", "default": 3000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a full-page screenshot of a URL. Returns the screenshot as base64 image.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to screenshot"},
                "wait_ms": {"type": "integer", "description": "Wait time in ms after load", "default": 3000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_measure",
        "description": "Measure computed CSS styles of an element on a page. Use to verify if implementation matches design tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the page"},
                "selector": {"type": "string", "description": "CSS selector of the element"},
                "properties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CSS properties to measure (e.g. ['font-size', 'color', 'padding-top'])",
                },
                "wait_ms": {"type": "integer", "default": 3000},
            },
            "required": ["url", "selector", "properties"],
        },
    },
    {
        "name": "browser_measure_all",
        "description": "Measure computed CSS styles of ALL elements matching a selector. Returns an array of measurements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "selector": {"type": "string"},
                "properties": {"type": "array", "items": {"type": "string"}},
                "wait_ms": {"type": "integer", "default": 3000},
            },
            "required": ["url", "selector", "properties"],
        },
    },
    {
        "name": "intake_extract",
        "description": "Extract design tokens from a Figma frame. Returns a structured contract with typography, colors, spacing, sizes, and borders for each component.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_key": {"type": "string", "description": "Figma file key"},
                "node_id": {"type": "string", "description": "Figma node ID (e.g. '2337:4783')"},
            },
            "required": ["file_key", "node_id"],
        },
    },
    {
        "name": "verify_geometry",
        "description": "Compare a design contract (from intake) with the actual rendered page. Returns a list of mismatches between expected (Figma) and actual (browser) values. Each mismatch is a bug to fix.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the page to verify"},
                "contract": {"type": "object", "description": "Design contract from intake_extract"},
                "wait_ms": {"type": "integer", "default": 5000},
            },
            "required": ["url", "contract"],
        },
    },
    {
        "name": "memory_search",
        "description": "Search for relevant memories from previous executions. Use before starting a task to recall past learnings about this client/stack.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "client": {"type": "string", "description": "Client name", "default": ""},
                "stack": {"type": "string", "description": "Tech stack (e.g. 'VTEX IO')", "default": ""},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_add",
        "description": "Store a learning from this execution. Only use when something went wrong (QA failed, review rejected, verify failed). NO EVIDENCE = NO MEMORY.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "What was learned"},
                "client": {"type": "string", "default": ""},
                "stack": {"type": "string", "default": ""},
                "source": {"type": "string", "description": "Evidence source (e.g. 'verify_failed', 'review_rejected')", "default": "agent"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "skill_search",
        "description": "Search available skills in the workspace by keyword. Returns name and description of matching skills. Use this when you need knowledge about a topic (payments, marketplace, masterdata, etc.) that is not in your currently loaded skills.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword (e.g. 'payment', 'masterdata', 'marketplace', 'graphql')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "skill_read",
        "description": "Read the full content of a skill by its exact name. Use after skill_search to load the knowledge you need. The content is a detailed technical reference — read it before implementing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact skill name as returned by skill_search (e.g. 'vtex/payment-provider-protocol')"},
            },
            "required": ["name"],
        },
    },
]


# ── Skill helpers (direct DB access via DATABASE_URL) ──

def _get_db_url():
    """Resolve DB URL from env. Falls back to backend's DATABASE_URL."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Try reading from backend's env if on same network
        url = os.environ.get("SKILL_DATABASE_URL", "")
    return url


def _skill_search(query):
    """Search skills by keyword in name or description."""
    try:
        import psycopg2
    except ImportError:
        return json.dumps({"error": "psycopg2 not installed — skill tools unavailable"})
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "DATABASE_URL not set — skill tools unavailable"})
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        q = f"%{query.lower()}%"
        cur.execute(
            "SELECT name, description, length(content) AS chars "
            "FROM skill WHERE (LOWER(name) LIKE %s OR LOWER(description) LIKE %s) "
            "ORDER BY name LIMIT 20",
            (q, q),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = [{"name": r[0], "description": r[1], "content_chars": r[2]} for r in rows]
        return json.dumps({"query": query, "count": len(results), "skills": results})
    except Exception as e:
        return json.dumps({"error": f"DB query failed: {str(e)}"})


def _skill_read(name):
    """Read full content of a skill by exact name."""
    try:
        import psycopg2
    except ImportError:
        return json.dumps({"error": "psycopg2 not installed — skill tools unavailable"})
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "DATABASE_URL not set — skill tools unavailable"})
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, description, content FROM skill WHERE name = %s LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT name, description, content FROM skill WHERE name LIKE %s LIMIT 1",
                (f"%{name}%",),
            )
            row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return json.dumps({"error": f"Skill not found: {name}"})
        return json.dumps({"name": row[0], "description": row[1], "content": row[2]})
    except Exception as e:
        return json.dumps({"error": f"DB query failed: {str(e)}"})


# ── Tool execution ──

def execute_tool(name, args):
    if name == "browser_navigate":
        from browser import OdusBrowser
        with OdusBrowser() as b:
            result = b.navigate(args["url"], wait_ms=args.get("wait_ms", 3000))
            metrics = b.get_page_metrics()
            return json.dumps({
                "status": result.status,
                "console_errors": result.console_errors[:10],
                "network_errors": result.network_errors[:10],
                "load_time_ms": result.load_time_ms,
                "has_errors": result.has_errors,
                "title": metrics.get("title", ""),
                "element_count": metrics.get("elementCount", 0),
            })

    elif name == "browser_screenshot":
        from browser import OdusBrowser
        import base64
        tmp = tempfile.mktemp(suffix=".png")
        with OdusBrowser() as b:
            b.navigate(args["url"], wait_ms=args.get("wait_ms", 3000))
            path = b.screenshot(tmp)
            if path:
                data = base64.b64encode(Path(path).read_bytes()).decode()
                Path(path).unlink(missing_ok=True)
                return json.dumps({"image": f"data:image/png;base64,{data[:100]}...", "size": len(data)})
            return json.dumps({"error": "Failed to take screenshot"})

    elif name == "browser_measure":
        from browser import OdusBrowser
        with OdusBrowser() as b:
            b.navigate(args["url"], wait_ms=args.get("wait_ms", 3000))
            result = b.measure_element(args["selector"], args["properties"])
            if result is None:
                return json.dumps({"error": f"Element not found: {args['selector']}"})
            return json.dumps({"selector": args["selector"], "styles": result})

    elif name == "browser_measure_all":
        from browser import OdusBrowser
        with OdusBrowser() as b:
            b.navigate(args["url"], wait_ms=args.get("wait_ms", 3000))
            results = b.measure_all(args["selector"], args["properties"])
            return json.dumps({"selector": args["selector"], "count": len(results), "elements": results[:20]})

    elif name == "intake_extract":
        from intake import DesignIntake
        intake = DesignIntake()
        contract = intake.extract(args["file_key"], args["node_id"])
        return json.dumps(contract)

    elif name == "verify_geometry":
        from verify_geometry import GeometryVerifier
        verifier = GeometryVerifier()
        result = verifier.verify(args["url"], args["contract"], wait_ms=args.get("wait_ms", 5000))
        return json.dumps({
            "total_checks": result.total_checks,
            "passed": result.passed,
            "failed": result.failed,
            "pass_rate": result.pass_rate,
            "is_passing": result.is_passing,
            "diffs": result.to_dict().get("diffs", []),
            "fix_prompt": result.to_prompt() if not result.is_passing else "All checks passed.",
        })

    elif name == "memory_search":
        from memory import OdusMemory
        mem = OdusMemory()
        if not mem.available:
            return json.dumps({"available": False, "results": []})
        results = mem.search(args["query"], client=args.get("client", ""), stack=args.get("stack", ""), limit=args.get("limit", 5))
        return json.dumps({"available": True, "results": results})

    elif name == "memory_add":
        from memory import OdusMemory
        mem = OdusMemory()
        if not mem.available:
            return json.dumps({"available": False})
        mid = mem.add(args["content"], client=args.get("client", ""), stack=args.get("stack", ""), source=args.get("source", "agent"))
        return json.dumps({"available": True, "id": mid})

    elif name == "skill_search":
        return _skill_search(args["query"])

    elif name == "skill_read":
        return _skill_read(args["name"])

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# ── MCP Protocol ──

def handle_message(msg):
    method = msg.get("method", "")
    id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        send_result(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "odus-tools", "version": "1.0.0"},
        })

    elif method == "notifications/initialized":
        pass  # no response needed

    elif method == "tools/list":
        send_result(id, {"tools": TOOLS})

    elif method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = execute_tool(name, args)
            send_result(id, {
                "content": [{"type": "text", "text": result}],
            })
        except Exception as e:
            send_result(id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            })

    elif id is not None:
        send_error(id, -32601, f"Method not found: {method}")


def main():
    while True:
        msg = read_message()
        if msg is None:
            break
        handle_message(msg)


if __name__ == "__main__":
    main()
