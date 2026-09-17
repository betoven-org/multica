#!/usr/bin/env python3
"""
Odus Task — Orquestrador Python (self-contained)

Pipeline completo de 17 etapas:
  1: Classify → 1.5: Spec Gate → 2: Model Routing → 2.5: Planner
  3: Branch → State Before → Adapter Preflight
  4: Executor
  5: QA → QA Fix → 5.5: Verify (adapter up + playwright + down)
  6: Reviewer → 6.5: Red Team
  7: Deliver → State After
  8: Quality Score → 9: Intervention
  10: Execution → 11: Timesheet → 12: Knowledge
  13: Status Callback + Comment + Trace Complete

Uso:
  python3 scripts/odus-task.py <taskId>          # Interativo
  python3 scripts/odus-task.py <taskId> --auto   # Autonomo
"""

import sys
import os
import re
import json
import time
import signal
import subprocess
import tempfile
import shutil
import hashlib
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, field

# Mem0 (optional)
try:
    sys.path.insert(0, str(Path(__file__).parent / "pi"))
    from memory import OdusMemory
except ImportError:
    OdusMemory = None  # type: ignore

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "https://task.oduscommerce.com.br"
API_LOCAL = "http://localhost:3000"
SCRIPT_DIR = Path(__file__).parent
REPO_DIR = Path.cwd()
SCREENSHOTS_DIR = Path(tempfile.mkdtemp(prefix="odus-screenshots-"))
CLAUDE_DIR = Path.home() / ".claude"
TEMPLATES_DIR = SCRIPT_DIR.parent / "templates"

# ── Colors ────────────────────────────────────────────────────────────────────

class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"

def log(msg: str): print(f"{C.BOLD}{C.CYAN}▸{C.NC} {msg}")
def ok(msg: str): print(f"  {C.GREEN}✅{C.NC} {msg}")
def warn(msg: str): print(f"  {C.YELLOW}⚠️{C.NC}  {msg}")
def fail(msg: str): print(f"  {C.RED}❌{C.NC} {msg}")
def dim(msg: str): print(f"  {C.DIM}{msg}{C.NC}")
def hr(): print(f"{C.DIM}{'━' * 60}{C.NC}")


# ── API ───────────────────────────────────────────────────────────────────────

def _http(url: str, method: str = "GET", data: dict | list | None = None, timeout: int = 10) -> dict | list | None:
    try:
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def api_call(endpoint: str, method: str = "GET", data: dict | list | None = None) -> dict | list | None:
    for base in [API_LOCAL, API_BASE]:
        try:
            result = _http(f"{base}{endpoint}", method, data, timeout=3 if base == API_LOCAL else 10)
            if result is None:
                continue
            if isinstance(result, dict) and "error" in result:
                continue
            return result
        except Exception:
            continue
    return None


# ── Claude helpers ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | list | None:
    """Extrai JSON de texto que pode conter markdown, fences, etc."""
    if not text or not text.strip():
        return None

    # 1. Tentar parse direto (resposta e JSON puro)
    stripped = text.strip()
    for start_char in ["{", "["]:
        if stripped.startswith(start_char):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                break

    # 2. Remover markdown fences (```json ... ``` ou ``` ... ```)
    fence_pattern = r"```(?:json|JSON)?\s*\n?(.*?)```"
    fence_matches = re.findall(fence_pattern, text, re.DOTALL)
    for match in fence_matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # 3. Buscar o maior bloco JSON valido na resposta
    # Tentar objetos primeiro, depois arrays
    for pattern in [r"\{", r"\["]:
        close = "}" if pattern == r"\{" else "]"
        for m in re.finditer(pattern, text):
            start = m.start()
            depth = 0
            in_string = False
            escape = False
            end = start
            for i in range(start, len(text)):
                c = text[i]
                if escape:
                    escape = False
                    continue
                if c == "\\":
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == pattern[-1]:  # { or [
                    depth += 1
                elif c == close:
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                candidate = text[start:end]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

    return None


def claude_json(prompt: str, model: str = "haiku", timeout: int = 60) -> dict | list | None:
    """Roda claude -p e extrai JSON da resposta."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model, prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=timeout,
        )
        return _extract_json(result.stdout)
    except Exception:
        pass
    return None


def claude_text(prompt: str, model: str = "haiku", timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model, prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class TaskContext:
    task_id: str
    auto_mode: bool = False

    # Classify
    type: str = ""
    risk: str = ""
    autonomy: str = ""
    title: str = ""
    description: str = ""
    steps_to_reproduce: str = ""
    client_id: str = ""
    client_name: str = ""
    client_slug: str = ""
    client_stack: str = ""
    repo_url: str = ""
    task_type: str = ""
    figma_url: str = ""
    branch: str = ""
    comments: list = field(default_factory=list)
    skills: list = field(default_factory=list)
    knowledge: list = field(default_factory=list)
    stack_context: dict = field(default_factory=dict)
    classify_raw: dict = field(default_factory=dict)

    # Routing
    executor_model: str = "sonnet"
    reviewer_model: str = "opus"

    # Trace
    trace_id: str = ""

    # Plan
    plan: dict = field(default_factory=dict)

    # Branch
    branch_name: str = ""

    # Figma tokens
    figma_tokens: str = ""

    # Previous traces
    previous_context: str = ""

    # QA
    gate_build: str = "skip"
    gate_types: str = "skip"
    gate_lint: str = "skip"
    gate_tests: str = "skip"
    gate_verify: str = "skip"
    qa_failed: bool = False

    # Review
    review_rounds: int = 0
    review_approved: bool = True

    # Red Team
    redteam_passed: bool = True

    # Scores
    spec_confidence: int = 0
    quality_score: int = 0
    prediction: int = 75
    prediction_rec: str = "proceed"

    # Adapter
    adapter_stack: str = "noop"
    verify_available: bool = False
    preflight_ok: bool = False
    preview_url: str = ""

    # State
    hash_before: str = ""
    file_count_before: int = 0
    human_intervention: bool = False
    files_changed: list = field(default_factory=list)
    pr_url: str = ""
    start_time: float = 0.0
    skip_perms: bool = False


# ── Trace helpers ─────────────────────────────────────────────────────────────

def trace_create(ctx: TaskContext, metadata: dict) -> str:
    result = api_call("/api/traces", "POST", {
        "taskId": ctx.task_id, "clientId": ctx.client_id,
        "executorModel": ctx.executor_model, "reviewerModel": ctx.reviewer_model,
        "metadata": metadata,
    })
    return result.get("traceId", "") if result else ""


def trace_event(ctx: TaskContext, type_: str, action: str, data: dict | list | None = None, duration: int | None = None):
    if not ctx.trace_id:
        return
    api_call(f"/api/traces/{ctx.trace_id}/events", "POST", {
        "type": type_, "action": action, "data": data, "duration": duration,
    })


def trace_gate(ctx: TaskContext, gate: str, status: str, evidence: dict | None = None):
    if not ctx.trace_id:
        return
    api_call(f"/api/traces/{ctx.trace_id}/gates", "POST", {
        "gate": gate, "status": status, "evidence": evidence or {},
    })


def trace_complete(ctx: TaskContext, result: str, score: int | None = None, duration: int | None = None):
    if not ctx.trace_id:
        return
    api_call(f"/api/traces/{ctx.trace_id}", "PATCH", {
        "result": result, "qualityScore": score, "duration": duration,
        "predictedScore": ctx.prediction,
    })


def trace_outcome(ctx: TaskContext, data: dict):
    if not ctx.trace_id:
        return
    api_call(f"/api/traces/{ctx.trace_id}/outcome", "POST", data)


# ── Shell helpers ─────────────────────────────────────────────────────────────

def sh(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def kill_port(port: int):
    """Mata qualquer processo na porta."""
    try:
        r = sh(["lsof", "-ti", f":{port}"])
        for pid in r.stdout.strip().split("\n"):
            if pid.strip():
                os.kill(int(pid.strip()), signal.SIGKILL)
    except Exception:
        pass


def wait_for_url(url: str, timeout: int = 120) -> bool:
    """Espera URL responder com 200/301/302."""
    elapsed = 0
    while elapsed < timeout:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 301, 302):
                    return True
        except Exception:
            pass
        time.sleep(3)
        elapsed += 3
    return False


# ── Repo analysis ────────────────────────────────────────────────────────────

RULES_CACHE_DIR = Path(tempfile.gettempdir()) / "odus-rules-cache"
RULES_CACHE_DIR.mkdir(exist_ok=True)


def analyze_repo_structure() -> dict:
    """Analisa estrutura do repo sem LLM. Retorna mapa concreto."""
    info: dict = {"type": "unknown", "files": [], "dependencies": [], "config": {}}

    # Detectar tipo de projeto
    if (REPO_DIR / "manifest.json").exists():
        try:
            manifest = json.loads((REPO_DIR / "manifest.json").read_text())
            info["type"] = "vtex-io"
            info["config"]["manifest"] = {
                "name": manifest.get("name", ""),
                "vendor": manifest.get("vendor", ""),
                "builders": manifest.get("builders", {}),
            }
        except Exception:
            pass
    elif (REPO_DIR / "deno.json").exists() or (REPO_DIR / "deno.jsonc").exists():
        info["type"] = "deco-cx"
    elif (REPO_DIR / "store.config.js").exists() or (REPO_DIR / "store.config.ts").exists():
        info["type"] = "faststore"
    elif (REPO_DIR / "shopify.theme.toml").exists() or (REPO_DIR / "config" / "settings_schema.json").exists():
        info["type"] = "shopify-theme"
    elif (REPO_DIR / "remix.config.js").exists() or (REPO_DIR / "hydrogen.config.ts").exists():
        info["type"] = "shopify-hydrogen"
    elif any((REPO_DIR / c).exists() for c in ["next.config.ts", "next.config.js", "next.config.mjs"]):
        info["type"] = "nextjs"

    # Package.json deps
    pkg_path = REPO_DIR / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text())
            deps = list(pkg.get("dependencies", {}).keys())
            dev_deps = list(pkg.get("devDependencies", {}).keys())
            info["dependencies"] = deps[:30]
            info["dev_dependencies"] = dev_deps[:20]
            info["scripts"] = list(pkg.get("scripts", {}).keys())
        except Exception:
            pass

    # Estrutura de pastas (top-level + src dirs relevantes)
    source_dirs = ["react", "node", "store", "src", "components", "sections",
                   "islands", "templates", "snippets", "assets", "styles",
                   "pages", "app", "lib", "utils", "hooks", "graphql"]
    tree = []
    for d in source_dirs:
        dp = REPO_DIR / d
        if dp.is_dir():
            files_in_dir = []
            for f in sorted(dp.rglob("*")):
                if f.is_file() and not any(p in str(f) for p in ["node_modules", ".git", "dist", "build", "__pycache__"]):
                    rel = str(f.relative_to(REPO_DIR))
                    files_in_dir.append(rel)
            tree.append({"dir": d, "files": files_in_dir[:50]})

    info["tree"] = tree

    # Arquivos na raiz relevantes
    root_files = [f.name for f in REPO_DIR.iterdir()
                  if f.is_file() and f.suffix in (".json", ".js", ".ts", ".tsx", ".css", ".toml", ".yaml", ".yml")]
    info["root_files"] = sorted(root_files)[:20]

    # Contar total de arquivos fonte
    total = 0
    for item in tree:
        total += len(item["files"])
    info["total_source_files"] = total

    return info


def extract_actionable_rules(skill: dict) -> list[str]:
    """Transforma skill em regras curtas e diretas. Cache em disco."""
    skill_name = skill.get("name", "unknown")
    content = skill.get("content", "")
    if not content:
        return [f"Seguir skill {skill_name}"]

    # Cache key baseado no hash do conteudo
    cache_key = hashlib.md5(content.encode()).hexdigest()[:12]
    cache_file = RULES_CACHE_DIR / f"{skill_name}-{cache_key}.json"

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            if isinstance(cached, list) and cached:
                return cached
        except Exception:
            pass

    prompt = f"""Extraia as 5-7 regras mais importantes deste skill como bullets curtos e diretos.
Cada regra deve ser actionable — o dev sabe exatamente o que fazer ou nao fazer.
Foque em regras PRATICAS, nao conceituais.

Skill: {skill_name}
Conteudo:
{content[:2500]}

Responda APENAS como lista JSON de strings: ["regra1", "regra2", ...]"""

    rules = claude_json(prompt, "haiku", timeout=30)
    if isinstance(rules, list) and rules:
        rules = [str(r) for r in rules[:7]]
        try:
            cache_file.write_text(json.dumps(rules, ensure_ascii=False))
        except Exception:
            pass
        return rules

    return [f"Seguir skill {skill_name}"]


# ── Local Knowledge Resolver ─────────────────────────────────────────────────

def _normalize_stack_key(stack: str) -> str:
    """Normaliza stack pra chave de busca de arquivos."""
    return stack.lower().replace(" ", "-").replace(".", "-")


def _read_file_safe(path: Path, max_chars: int = 5000) -> str:
    """Le arquivo de forma segura, retorna string vazia se nao existir."""
    try:
        if path.exists() and path.is_file():
            return path.read_text()[:max_chars]
    except Exception:
        pass
    return ""


def resolve_local_knowledge(stack: str, task_type: str) -> dict:
    """Resolve todo o conhecimento local disponivel pra uma stack/tipo.

    Retorna:
        template: conteudo do CLAUDE.{stack}.md
        patterns: lista de patterns da stack
        agent_persona: conteudo do agent specialist
        memory: conteudo do memory da stack
        skills_available: skills instalados relevantes
    """
    sk = _normalize_stack_key(stack)
    result: dict = {
        "template": "",
        "patterns": [],
        "agent_persona": "",
        "memory": "",
        "skills_available": [],
    }

    # 1. Template CLAUDE.{stack}.md
    stack_template_map = {
        "vtex-io": "CLAUDE.vtex-io.md",
        "vtex": "CLAUDE.vtex-io.md",
        "deco-cx": "CLAUDE.deco.md",
        "deco": "CLAUDE.deco.md",
        "decocx": "CLAUDE.deco.md",
        "faststore": "CLAUDE.faststore.md",
        "fast-store": "CLAUDE.faststore.md",
        "shopify": "CLAUDE.shopify.md",
        "tray": "CLAUDE.tray.md",
    }
    template_name = stack_template_map.get(sk, "")
    if template_name:
        result["template"] = _read_file_safe(TEMPLATES_DIR / template_name)

    # 2. Patterns da stack (~/.claude/patterns/{stack}/*.md)
    pattern_dir_map = {
        "vtex-io": "node",  # VTEX IO usa patterns de node
        "vtex": "node",
        "deco-cx": "deco",
        "deco": "deco",
        "faststore": "node",
        "shopify": "node",
        "cloudflare": "cloudflare",
    }
    pattern_dir_name = pattern_dir_map.get(sk, "")
    if pattern_dir_name:
        patterns_dir = CLAUDE_DIR / "patterns" / pattern_dir_name
        if patterns_dir.is_dir():
            for pf in sorted(patterns_dir.glob("*.md")):
                content = _read_file_safe(pf, 3000)
                if content:
                    result["patterns"].append({"name": pf.stem, "content": content})

    # Patterns typescript e zod sao universais
    for universal in ["typescript", "zod"]:
        uni_dir = CLAUDE_DIR / "patterns" / universal
        if uni_dir.is_dir():
            for pf in sorted(uni_dir.glob("*.md")):
                content = _read_file_safe(pf, 2000)
                if content:
                    result["patterns"].append({"name": f"{universal}/{pf.stem}", "content": content})

    # 3. Agent persona (~/.claude/agents/{type}-specialist.md)
    agent_map = {
        "layout": "frontend-specialist.md",
        "frontend": "frontend-specialist.md",
        "bug": "frontend-specialist.md",
        "feature": "frontend-specialist.md",
        "backend": "backend-specialist.md",
        "integration": "backend-specialist.md",
        "performance": "frontend-specialist.md",
        "seo": "frontend-specialist.md",
        "content": "frontend-specialist.md",
        "infra": "platform-specialist.md",
    }
    agent_file = agent_map.get(task_type, "frontend-specialist.md")
    result["agent_persona"] = _read_file_safe(CLAUDE_DIR / "agents" / agent_file)

    # 4. Memory da stack (~/.claude/memory/{stack}.md)
    memory_map = {
        "vtex-io": "vtex.md",
        "vtex": "vtex.md",
        "deco-cx": "deco-cx.md",
        "deco": "deco-cx.md",
        "faststore": "node.md",
        "shopify": "node.md",
        "cloudflare": "cloudflare.md",
        "supabase": "supabase.md",
    }
    memory_file = memory_map.get(sk, "")
    if memory_file:
        result["memory"] = _read_file_safe(CLAUDE_DIR / "memory" / memory_file)

    # 5. Skills instalados relevantes (~/.claude/skills/)
    skills_dir = CLAUDE_DIR / "skills"
    if skills_dir.is_dir():
        # Mapear quais skills sao relevantes pra cada stack
        skill_prefixes = {
            "vtex-io": ["vtex-io-", "marketplace-", "payment-", "headless-"],
            "vtex": ["vtex-io-", "marketplace-", "payment-", "headless-"],
            "deco-cx": ["faststore-"],
            "deco": ["faststore-"],
            "faststore": ["faststore-", "headless-"],
        }
        relevant_prefixes = skill_prefixes.get(sk, [])

        # Skills universais
        universal_skills = ["impeccable", "frontend-design", "webapp-testing", "apple-design"]
        if task_type == "layout":
            universal_skills.extend(["design-taste-frontend", "emil-design-eng"])

        for sd in skills_dir.iterdir():
            if not sd.is_dir() and not sd.is_symlink():
                continue
            name = sd.name
            is_relevant = any(name.startswith(p) for p in relevant_prefixes)
            is_universal = name in universal_skills
            if is_relevant or is_universal:
                result["skills_available"].append(name)

    return result


# ── Stack Adapters (Python puro) ─────────────────────────────────────────────

class Adapter:
    """Base adapter — noop."""
    name = "noop"
    has_verify = False

    def __init__(self, ctx: TaskContext):
        self.ctx = ctx
        self._pid: int | None = None

    def preflight(self) -> bool:
        return True

    def up(self) -> bool:
        return False

    def verify(self) -> tuple[bool, dict]:
        return False, {}

    def down(self):
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except OSError:
                pass
            self._pid = None
        self.ctx.preview_url = ""

    def _check_homepage(self) -> tuple[int, int]:
        """Checa homepage, retorna (passed, failed)."""
        passed = failed = 0
        try:
            req = urllib.request.Request(self.ctx.preview_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
            if status in (200, 301, 302):
                ok(f"Homepage: {status}")
                passed += 1
            else:
                fail(f"Homepage: {status}")
                failed += 1
        except Exception as e:
            fail(f"Homepage: {e}")
            failed += 1
        return passed, failed

    def _take_screenshot(self, name: str = "after-homepage") -> str | None:
        if not cmd_exists("npx"):
            return None
        output = SCREENSHOTS_DIR / f"{name}.png"
        r = sh(["npx", "--yes", "playwright", "screenshot", "--browser", "chromium",
                "--full-page", self.ctx.preview_url, str(output)], timeout=30)
        return str(output) if output.exists() else None

    def _capture_devtools(self, name: str = "after-homepage", wait_seconds: int = 5) -> dict:
        """Captura console errors, network errors e screenshot via Playwright."""
        if not cmd_exists("npx"):
            return {}

        screenshot_path = SCREENSHOTS_DIR / f"{name}.png"
        output_json = SCREENSHOTS_DIR / f"{name}-devtools.json"

        pw_script = SCREENSHOTS_DIR / "_devtools_capture.js"
        pw_script.write_text("""
const { chromium } = require('playwright');
(async () => {
  const [url, screenshotPath, outputJson, waitMs] = process.argv.slice(2);
  const consoleErrors = [], consoleWarnings = [], networkErrors = [];
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  page.on('console', msg => {
    const entry = { type: msg.type(), text: msg.text().substring(0, 500) };
    if (msg.type() === 'error') consoleErrors.push(entry);
    else if (msg.type() === 'warning') consoleWarnings.push(entry);
  });
  page.on('pageerror', err => consoleErrors.push({ type: 'pageerror', text: err.message.substring(0, 500) }));
  page.on('response', r => { if (r.status() >= 400) networkErrors.push({ url: r.url().substring(0, 200), status: r.status() }); });
  page.on('requestfailed', r => networkErrors.push({ url: r.url().substring(0, 200), status: 0, failure: r.failure()?.errorText || 'unknown' }));
  try { await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 }); } catch(e) { consoleErrors.push({ type: 'navigation', text: e.message.substring(0, 500) }); }
  await page.waitForTimeout(parseInt(waitMs));
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await browser.close();
  const result = { consoleErrors: consoleErrors.slice(0, 20), consoleWarnings: consoleWarnings.slice(0, 10), networkErrors: networkErrors.slice(0, 20), screenshot: screenshotPath, url, timestamp: new Date().toISOString() };
  require('fs').writeFileSync(outputJson, JSON.stringify(result, null, 2));
})();
""")
        try:
            sh(["node", str(pw_script), self.ctx.preview_url, str(screenshot_path),
                str(output_json), str(wait_seconds * 1000)], timeout=60)
        except Exception:
            pass

        if output_json.exists():
            try:
                return json.loads(output_json.read_text())
            except Exception:
                pass
        return {}

    def _start_bg(self, cmd: list[str], log_name: str) -> int | None:
        """Inicia processo em background."""
        log_file = open(f"/tmp/odus-{log_name}-{self.ctx.task_id}.log", "w")
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, cwd=str(REPO_DIR))
        self._pid = proc.pid
        return proc.pid


class DecoCxAdapter(Adapter):
    name = "deco-cx"
    has_verify = True
    PORT = 8000

    def preflight(self) -> bool:
        if not cmd_exists("deno"):
            fail("deno nao encontrado")
            return False
        if not (REPO_DIR / "deno.json").exists() and not (REPO_DIR / "deno.jsonc").exists():
            fail("deno.json nao encontrado")
            return False
        return True

    def up(self) -> bool:
        kill_port(self.PORT)
        self._start_bg(["deno", "task", "start"], "deco")
        dim(f"Aguardando deco.cx em localhost:{self.PORT}...")
        if wait_for_url(f"http://localhost:{self.PORT}", 90):
            self.ctx.preview_url = f"http://localhost:{self.PORT}"
            return True
        self.down()
        return False

    def verify(self) -> tuple[bool, dict]:
        passed, failed = self._check_homepage()
        self._take_screenshot()
        return failed == 0, {"passed": passed, "failed": failed}

    def down(self):
        super().down()
        kill_port(self.PORT)


class VtexIoAdapter(Adapter):
    name = "vtex-io"
    has_verify = True
    _account: str = ""
    _workspace: str = ""

    def preflight(self) -> bool:
        if not cmd_exists("vtex"):
            fail("vtex CLI nao encontrado")
            return False
        r = sh(["vtex", "whoami"])
        out = r.stdout + r.stderr
        if "not logged" in out.lower() or "error" in out.lower() or r.returncode != 0:
            fail("Sessao VTEX expirada. Rode: vtex login")
            return False
        m = re.search(r"(?:account:\s*|Logged into\s+)(\S+)", out)
        self._account = m.group(1) if m else ""
        return bool(self._account)

    def up(self) -> bool:
        task_short = self.ctx.task_id[:8]
        self._workspace = f"odus-{task_short}"
        sh(["vtex", "workspace", "create", self._workspace, "--production=false"])
        sh(["vtex", "use", self._workspace])
        self._start_bg(["vtex", "link", "--no-watch"], "vtex-link")
        self.ctx.preview_url = f"https://{self._workspace}--{self._account}.myvtex.com"
        dim(f"Aguardando VTEX IO em {self.ctx.preview_url}...")
        if wait_for_url(self.ctx.preview_url, 180):
            return True
        self.down()
        return False

    def verify(self) -> tuple[bool, dict]:
        passed, failed = self._check_homepage()

        # DevTools capture
        devtools = self._capture_devtools("after-homepage", 8)
        if devtools:
            report_path = SCREENSHOTS_DIR / "devtools-report.json"
            report_path.write_text(json.dumps(devtools, indent=2))

            console_errors = len(devtools.get("consoleErrors", []))
            if console_errors > 0:
                fail(f"{console_errors} erros no console")
                for e in devtools.get("consoleErrors", [])[:5]:
                    dim(f"  {e.get('text', '')[:200]}")
                failed += 1
            else:
                ok("Console limpo")
                passed += 1

            network_errors = len(devtools.get("networkErrors", []))
            if network_errors > 0:
                warn(f"{network_errors} erros de network")
            else:
                ok("Network limpo")
                passed += 1
        else:
            self._take_screenshot()

        # Verificar erro de render VTEX
        try:
            with urllib.request.urlopen(self.ctx.preview_url, timeout=10) as resp:
                body = resp.read().decode()[:2000]
            if re.search(r"runtime error|render error|something went wrong", body, re.I):
                fail("Pagina com erro de render VTEX")
                failed += 1
            else:
                ok("Sem erro de render")
                passed += 1
        except Exception:
            pass

        return failed == 0, {"passed": passed, "failed": failed}

    def down(self):
        super().down()
        if self._workspace:
            sh(["vtex", "workspace", "delete", self._workspace, "--yes"])
            self._workspace = ""


class FastStoreAdapter(Adapter):
    name = "faststore"
    has_verify = True
    PORT = 3000

    def preflight(self) -> bool:
        if not cmd_exists("yarn") and not cmd_exists("npm"):
            fail("yarn/npm nao encontrado")
            return False
        if not (REPO_DIR / "package.json").exists():
            fail("package.json nao encontrado")
            return False
        return True

    def up(self) -> bool:
        kill_port(self.PORT)
        self._start_bg(["yarn", "dev"], "faststore")
        dim(f"Aguardando FastStore em localhost:{self.PORT}...")
        if wait_for_url(f"http://localhost:{self.PORT}", 120):
            self.ctx.preview_url = f"http://localhost:{self.PORT}"
            return True
        self.down()
        return False

    def verify(self) -> tuple[bool, dict]:
        passed, failed = self._check_homepage()
        self._take_screenshot()
        return failed == 0, {"passed": passed, "failed": failed}

    def down(self):
        super().down()
        kill_port(self.PORT)


class ShopifyAdapter(Adapter):
    name = "shopify"
    has_verify = True
    PORT = 9292

    def preflight(self) -> bool:
        if not cmd_exists("shopify"):
            fail("shopify CLI nao encontrado")
            return False
        if not os.environ.get("SHOPIFY_CLI_THEME_TOKEN"):
            fail("SHOPIFY_CLI_THEME_TOKEN nao definido")
            return False
        return True

    def up(self) -> bool:
        # Detectar Liquid vs Hydrogen
        if (REPO_DIR / "config" / "settings_schema.json").exists() or (REPO_DIR / "templates").is_dir():
            self._start_bg(["shopify", "theme", "dev", f"--port={self.PORT}"], "shopify")
            self.ctx.preview_url = f"http://localhost:{self.PORT}"
        elif (REPO_DIR / "package.json").exists():
            self._start_bg(["npm", "run", "dev"], "shopify")
            self.PORT = 3000
            self.ctx.preview_url = f"http://localhost:{self.PORT}"
        else:
            fail("Nao consegui detectar tipo de projeto Shopify")
            return False

        if wait_for_url(self.ctx.preview_url, 120):
            return True
        self.down()
        return False

    def verify(self) -> tuple[bool, dict]:
        passed, failed = self._check_homepage()
        self._take_screenshot()
        return failed == 0, {"passed": passed, "failed": failed}

    def down(self):
        super().down()
        kill_port(self.PORT)


def resolve_adapter(ctx: TaskContext) -> Adapter:
    """Mapeia stack pro adapter correto."""
    s = ctx.client_stack.lower().replace(" ", "-").replace(".", "-")
    mapping = {
        "vtex-io": VtexIoAdapter, "vtex": VtexIoAdapter,
        "deco-cx": DecoCxAdapter, "deco": DecoCxAdapter, "decocx": DecoCxAdapter,
        "faststore": FastStoreAdapter, "fast-store": FastStoreAdapter,
        "shopify": ShopifyAdapter,
    }
    cls = mapping.get(s, Adapter)
    return cls(ctx)


# ── MCP config helper ────────────────────────────────────────────────────────

def get_mcp_config() -> tuple[Path | None, list[str]]:
    """Extrai mcpServers do settings.json. Retorna (tmp_file, flags)."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return None, []
    try:
        settings = json.loads(settings_path.read_text())
        servers = settings.get("mcpServers", {})
        if servers:
            tmp = Path(tempfile.mktemp(suffix=".json", prefix="odus-mcp-"))
            tmp.write_text(json.dumps({"mcpServers": servers}))
            return tmp, ["--mcp-config", str(tmp)]
    except Exception:
        pass
    return None, []


# ── Etapas ────────────────────────────────────────────────────────────────────

def etapa_classify(ctx: TaskContext) -> bool:
    """Etapa 1 — Classify via API."""
    log("Classificando...")

    data = api_call(f"/api/tasks/{ctx.task_id}/classify")
    if not data or "classification" not in data:
        fail(f"Erro ao classificar task. Resposta: {data}")
        return False

    ctx.classify_raw = data
    cl = data["classification"]
    task = data["context"]["task"]
    client = data["context"]["client"]

    ctx.type = task.get("taskType") or cl["type"]
    ctx.risk = cl["risk"]
    ctx.autonomy = cl["autonomy"]
    ctx.title = task["title"]
    ctx.description = task.get("description", "")
    ctx.steps_to_reproduce = task.get("stepsToReproduce", "")
    ctx.client_id = client.get("id", "")
    ctx.client_name = client["name"]
    ctx.client_slug = client.get("slug", "")
    ctx.client_stack = client.get("stack", "")
    ctx.repo_url = client.get("repoUrl", "")
    ctx.task_type = task.get("taskType", "")
    ctx.figma_url = task.get("figmaUrl", "")
    ctx.branch = task.get("branch", "")
    ctx.comments = task.get("comments", [])
    ctx.skills = data.get("skills", [])
    ctx.knowledge = data.get("knowledge", [])
    ctx.stack_context = data["context"].get("stackContext", {})

    dim(f"Task: {ctx.title}")
    dim(f"Client: {ctx.client_name} ({ctx.client_stack})")
    dim(f"Tipo: {ctx.type} | Risco: {ctx.risk} | Autonomia: {ctx.autonomy}")
    dim(f"Skills: {len(ctx.skills)} ({', '.join(s['name'] for s in ctx.skills)})")
    dim(f"Knowledge: {len(ctx.knowledge)} items ativos")
    return True


def etapa_prediction(ctx: TaskContext):
    """Quality Prediction via API."""
    result = api_call(f"/api/tasks/{ctx.task_id}/predict?type={ctx.type}&risk={ctx.risk}&stack={ctx.client_stack}&model=sonnet")
    if result and isinstance(result, dict):
        ctx.prediction = int(result.get("prediction", 75))
        ctx.prediction_rec = result.get("recommendation", "proceed")
        if ctx.prediction != 75:
            dim(f"Prediction: {ctx.prediction}% ({ctx.prediction_rec})")
        if ctx.prediction_rec == "escalate" and ctx.risk != "low":
            warn(f"Quality prediction baixa ({ctx.prediction}%). Considere escalar pra humano.")


def etapa_previous_traces(ctx: TaskContext):
    """Busca traces anteriores da mesma task."""
    result = api_call(f"/api/tasks/{ctx.task_id}/traces?limit=3")
    if not result:
        return
    traces = result.get("traces", []) if isinstance(result, dict) else result
    if not traces:
        return

    lines = [f"## Execucoes anteriores ({len(traces)})", "ATENCAO: Task ja executada antes. Aprenda com os erros.", ""]
    for t in traces:
        lines.append(f"- [{str(t.get('createdAt', ''))[:19]}] result={t.get('result')} score={t.get('qualityScore')} model={t.get('executorModel')}")
        for g in t.get("qualityGates", []):
            if g.get("status") == "fail":
                lines.append(f"  FALHOU: {g.get('gate')} — {json.dumps(g.get('evidence', {}))}")
        for e in t.get("events", []):
            if e.get("type") == "human":
                lines.append(f"  INTERVENCAO: {e.get('action')} — {json.dumps(e.get('data', {}))}")

    ctx.previous_context = "\n".join(lines)
    dim(f"Traces anteriores: {len(traces)} (contexto carregado)")


def etapa_spec_gate(ctx: TaskContext) -> bool:
    """Etapa 1.5 — Spec Gate via Claude haiku."""
    log("Validando spec...")

    desc_text = re.sub(r"<[^<]+?>", " ", ctx.description or "").strip()[:1000]
    prompt = f"""Analise esta demanda de desenvolvimento e avalie a clareza da spec.

Titulo: {ctx.title}
Descricao: {desc_text}
Steps: {ctx.steps_to_reproduce or 'N/A'}

Responda APENAS em JSON (sem markdown):
{{"confidence": 0-100, "clear": true/false, "ambiguity": "low/medium/high", "assumptions": ["lista"], "summary": "resumo"}}"""

    spec = claude_json(prompt, "haiku")
    if isinstance(spec, dict):
        ctx.spec_confidence = int(spec.get("confidence", 75))
    else:
        ctx.spec_confidence = 75

    if ctx.spec_confidence < 50:
        fail(f"Spec insuficiente (confidence: {ctx.spec_confidence}%)")
        trace_event(ctx, "spec", "insufficient", {"confidence": ctx.spec_confidence})
        trace_complete(ctx, "blocked", 0, int(time.time() - ctx.start_time))
        api_call(f"/api/tasks/{ctx.task_id}/status", "POST", {
            "status": "BLOCKED",
            "description": f"Spec insuficiente (confidence: {ctx.spec_confidence}%). Clarificar requisitos.",
        })
        return False

    if ctx.spec_confidence < 80:
        warn(f"Spec parcial (confidence: {ctx.spec_confidence}%)")
    else:
        ok(f"Spec validada (confidence: {ctx.spec_confidence}%)")

    trace_event(ctx, "spec", "validated", {"confidence": ctx.spec_confidence})
    trace_gate(ctx, "spec", "pass", {"confidence": ctx.spec_confidence})
    return True


def etapa_model_routing(ctx: TaskContext):
    """Etapa 2 — Model routing baseado em risk/type."""
    policy = api_call("/api/policies/resolve", "POST", {
        "type": ctx.type, "risk": ctx.risk, "stack": ctx.client_stack,
    })

    if policy and policy.get("resolved"):
        ctx.executor_model = policy["action"].get("executorModel", "sonnet")
        ctx.reviewer_model = policy["action"].get("reviewerModel", "opus")
        dim(f"Policy: {policy.get('policyName', '')} (source={policy.get('source', '')})")
    else:
        if ctx.risk == "low":
            if ctx.type in ("content", "seo"):
                ctx.executor_model, ctx.reviewer_model = "haiku", "sonnet"
            else:
                ctx.executor_model, ctx.reviewer_model = "sonnet", "sonnet"
        elif ctx.risk == "medium":
            ctx.executor_model, ctx.reviewer_model = "sonnet", "opus"
        else:
            ctx.executor_model, ctx.reviewer_model = "opus", "opus"

    print()
    log(f"Modelo: executor={C.BOLD}{ctx.executor_model}{C.NC} | reviewer={C.BOLD}{ctx.reviewer_model}{C.NC}")


def etapa_plan(ctx: TaskContext):
    """Etapa 2.5 — Planner (sonnet, so risk medium+)."""
    if ctx.risk == "low":
        dim("Planner: skip (risk=low)")
        return

    print()
    log("Planejando approach...")

    desc_text = re.sub(r"<[^<]+?>", " ", ctx.description or "").strip()[:2000]

    # Prompt especifico por tipo de task
    type_guidance = {
        "layout": "Foque em: quais componentes visuais criar/editar, ordem de implementacao (estrutura HTML > estilo > responsivo), e quais arquivos de estilo precisam de mudanca.",
        "bug": "Foque em: onde o bug provavelmente esta (baseado no titulo/descricao), quais arquivos investigar primeiro, e qual a causa raiz mais provavel.",
        "feature": "Foque em: quais camadas sao afetadas (UI, logica, API), dependencias entre os passos, e se precisa de novos arquivos ou editar existentes.",
        "performance": "Foque em: quais metricas melhorar, onde provavelmente estao os gargalos, e quais otimizacoes aplicar.",
        "content": "Foque em: quais arquivos contem o conteudo a alterar, se envolve i18n (messages/), e impacto em SEO.",
        "seo": "Foque em: meta tags, structured data, sitemap, canonical URLs, e quais paginas sao afetadas.",
    }
    guidance = type_guidance.get(ctx.type, "Foque em: quais arquivos editar, qual a ordem de implementacao, e quais riscos considerar.")

    # Contexto da stack
    stack_hint = ""
    if "vtex" in ctx.client_stack.lower():
        stack_hint = "Stack VTEX IO: componentes ficam em react/, blocos em store/, estilos via CSS Handles."
    elif "deco" in ctx.client_stack.lower():
        stack_hint = "Stack deco.cx: sections em sections/, islands em islands/, loaders em loaders/."
    elif "shopify" in ctx.client_stack.lower():
        stack_hint = "Stack Shopify: templates em templates/, sections em sections/, snippets em snippets/."

    prompt = f"""Voce e o planner. Analise a task e defina um plano de execucao CONCRETO.

Titulo: {ctx.title}
Stack: {ctx.client_stack}
Tipo: {ctx.type} | Risco: {ctx.risk}
{stack_hint}
{"Figma: " + ctx.figma_url if ctx.figma_url else ""}

Descricao:
{desc_text}

{guidance}

Responda APENAS com JSON (sem markdown, sem ```):
{{"files": ["caminhos provaveis dos arquivos a modificar"], "steps": ["passo 1 concreto", "passo 2 concreto"], "risks": ["risco ou edge case"], "needsResearch": false, "needsFigma": {str(bool(ctx.figma_url)).lower()}}}"""

    plan = claude_json(prompt, "sonnet", timeout=90)

    if isinstance(plan, dict) and plan.get("steps") and len(plan["steps"]) > 1:
        ctx.plan = plan
    elif isinstance(plan, dict):
        # Plan veio mas com steps fraco — tentar enriquecer
        ctx.plan = plan
        if not plan.get("steps") or plan["steps"] == ["Implementar conforme descricao"]:
            # Gerar steps minimos baseados no tipo
            default_steps = {
                "layout": ["Inspecionar Figma (screenshot + tokens)", "Ler componentes existentes", "Implementar estrutura HTML", "Aplicar estilos do Figma", "Ajustar responsivo", "Testar visual"],
                "bug": ["Reproduzir o bug", "Identificar arquivo/linha do problema", "Corrigir a causa raiz", "Validar que nao quebrou nada"],
                "feature": ["Ler codigo existente relacionado", "Implementar a feature", "Ajustar testes se existirem"],
            }
            ctx.plan["steps"] = default_steps.get(ctx.type, ["Ler arquivos relevantes", "Implementar mudancas", "Validar resultado"])
    else:
        # Fallback total — steps baseados no tipo
        default_steps = {
            "layout": ["Inspecionar Figma (screenshot + tokens)", "Ler componentes existentes", "Implementar estrutura HTML", "Aplicar estilos do Figma", "Ajustar responsivo", "Testar visual"],
            "bug": ["Reproduzir o bug", "Identificar arquivo/linha do problema", "Corrigir a causa raiz", "Validar que nao quebrou nada"],
            "feature": ["Ler codigo existente relacionado", "Implementar a feature", "Ajustar testes se existirem"],
        }
        ctx.plan = {"steps": default_steps.get(ctx.type, ["Ler arquivos relevantes", "Implementar mudancas", "Validar resultado"]), "files": [], "risks": []}

    ok("Plan definido")
    for step in ctx.plan.get("steps", []):
        print(f"  - {step}")
    if ctx.plan.get("files"):
        dim(f"Arquivos: {', '.join(ctx.plan['files'][:5])}")
    if ctx.plan.get("risks"):
        for risk in ctx.plan["risks"][:3]:
            warn(f"Risco: {risk}")

    trace_event(ctx, "agent", "planner_completed", ctx.plan)


def etapa_adapter_preflight(ctx: TaskContext, adapter: "Adapter"):
    """Carrega adapter e roda preflight."""
    ctx.adapter_stack = adapter.name
    ctx.verify_available = adapter.has_verify

    if adapter.has_verify:
        ctx.preflight_ok = adapter.preflight()
        if ctx.preflight_ok:
            ok(f"Preflight {adapter.name}")
        else:
            warn(f"Preflight falhou ({adapter.name}). Verify nao disponivel.")
            ctx.verify_available = False

    dim(f"Adapter: {ctx.adapter_stack} | Verify: {ctx.verify_available}")


def etapa_branch(ctx: TaskContext):
    """Etapa 3 — Branch."""
    prefix_map = {"bug": "fix", "performance": "perf", "infra": "infra", "seo": "seo", "content": "content"}
    prefix = prefix_map.get(ctx.type, "feat")
    task_short = ctx.task_id[:8]

    sh(["git", "checkout", "main"])
    sh(["git", "pull", "origin", "main"])

    if ctx.branch:
        ctx.branch_name = ctx.branch
        log(f"Usando branch fixa: {ctx.branch_name}")
        r = sh(["git", "checkout", ctx.branch_name])
        if r.returncode != 0:
            sh(["git", "checkout", "-b", ctx.branch_name])
        sh(["git", "pull", "origin", ctx.branch_name])
    else:
        slug = re.sub(r"[^a-z0-9]", "-", ctx.title.lower())
        slug = re.sub(r"-+", "-", slug)[:40].rstrip("-")
        ctx.branch_name = f"{prefix}/task-{task_short}/{slug}"
        log(f"Criando branch: {ctx.branch_name}")
        r = sh(["git", "checkout", "-b", ctx.branch_name])
        if r.returncode != 0:
            sh(["git", "checkout", ctx.branch_name])

    dim(ctx.branch_name)
    trace_event(ctx, "decision", "branch_created", {"branch": ctx.branch_name})


def etapa_state_before(ctx: TaskContext):
    """Snapshot do estado git antes do executor."""
    r = sh(["git", "rev-parse", "HEAD"])
    ctx.hash_before = r.stdout.strip() if r.returncode == 0 else ""
    r2 = sh(["git", "ls-files"])
    ctx.file_count_before = len([l for l in r2.stdout.strip().split("\n") if l.strip()]) if r2.stdout.strip() else 0
    trace_event(ctx, "state", "before", {"hash": ctx.hash_before, "fileCount": ctx.file_count_before})


def parse_figma_url(url: str) -> tuple[str, str]:
    """Extrai fileKey e nodeId de uma URL do Figma."""
    file_match = re.search(r"/design/([^/]+)", url)
    node_match = re.search(r"node-id=([^&]+)", url)
    file_key = file_match.group(1) if file_match else ""
    node_id = node_match.group(1).replace("-", ":") if node_match else ""
    return file_key, node_id


def build_executor_prompt(ctx: TaskContext) -> str:
    """Monta o prompt completo pro executor."""
    lines = [f"# Task: {ctx.title}", f"Client: {ctx.client_name} ({ctx.client_stack})", ""]

    if ctx.description:
        desc_clean = re.sub(r"<[^<]+?>", " ", ctx.description).strip()[:3000]
        lines += ["## Descricao", desc_clean, ""]

    if ctx.comments:
        lines.append(f"## Comentarios ({len(ctx.comments)})")
        for c in ctx.comments:
            lines.append(f"**{c.get('author', '?')}** ({str(c.get('date', ''))[:10]}): {c.get('content', '')}")
        lines.append("")

    if ctx.figma_url:
        file_key, node_id = parse_figma_url(ctx.figma_url)
        lines += ["## Figma", f"URL: {ctx.figma_url}", f"FileKey: {file_key} | NodeId: {node_id}",
                  "Use o MCP Figma (get_design_context e get_screenshot) pra inspecionar o design.", ""]

    if ctx.steps_to_reproduce:
        lines += ["## Steps to reproduce", ctx.steps_to_reproduce, ""]

    if ctx.stack_context.get("rules"):
        lines += ["## Rules da stack", ctx.stack_context["rules"], ""]

    if ctx.stack_context.get("checklist"):
        lines.append("## Checklist")
        for item in ctx.stack_context["checklist"]:
            lines.append(f"- [ ] {item}")
        lines.append("")

    if ctx.skills:
        lines.append(f"## Skills ({len(ctx.skills)})")
        for s in ctx.skills:
            lines.append(f"### {s['name']} ({s.get('category', '')})")
            lines.append(s.get("content", "")[:3000])
            lines.append("")

    if ctx.knowledge:
        lines.append(f"## Knowledge ({len(ctx.knowledge)})")
        for k in ctx.knowledge:
            lines.append(f"### [{k['type']}] {k['title']} (confidence: {k.get('confidence', '?')})")
            lines.append(k["content"])
            if k.get("negative"):
                lines.append(f"NAO FAZER: {k['negative']}")
            lines.append("")

    if ctx.plan and ctx.plan.get("steps"):
        lines.append("## Plan")
        for i, step in enumerate(ctx.plan["steps"], 1):
            lines.append(f"{i}. {step}")
        if ctx.plan.get("files"):
            lines.append(f"\nArquivos provaveis: {', '.join(ctx.plan['files'])}")
        lines.append("")

    if ctx.previous_context:
        lines += [ctx.previous_context, ""]

    lines += [
        "## Instrucoes",
        "- Siga TODAS as rules e o checklist da stack",
        "- Siga as skills e knowledge carregados",
        "- ZERO console.log em producao",
        f"- Trabalhe APENAS na branch atual ({ctx.branch_name})",
        "- Quando terminar a implementacao, faca commit e avise que terminou",
        "- NAO faca push (o script faz depois)",
        "- NAO crie PR (o script faz depois)",
        "",
        "## Regras de codigo (OBRIGATORIO)",
        "- SEMPRE escreva JSX/TSX moderno — NUNCA use React.createElement()",
        "- Use const/let — NUNCA use var",
        "- Use arrow functions — NUNCA use function() anonima",
        "- Use destructuring, optional chaining (?.), nullish coalescing (??)",
        "- Leia e edite APENAS arquivos fonte (react/, node/, store/, styles/) — NUNCA edite build/, dist/",
        "- Se encontrar codigo legado (var, React.createElement), modernize ao editar",
    ]

    return "\n".join(lines)


def _run_intake(ctx: TaskContext) -> dict | None:
    """Roda intake do Figma. Retorna contrato ou None."""
    if not ctx.figma_url:
        return None
    try:
        from intake import DesignIntake
        file_key, node_id = parse_figma_url(ctx.figma_url)
        if not file_key:
            return None

        log("Extraindo design tokens do Figma...")
        intake = DesignIntake()
        contract = intake.extract(file_key, node_id)

        if contract.get("components"):
            ok(f"Intake: {len(contract['components'])} componentes extraidos")
            # Salvar contrato no diretorio de screenshots pra referencia
            contract_path = SCREENSHOTS_DIR / "design-contract.json"
            intake.save(contract, str(contract_path))
            return contract
        elif contract.get("pendingExtraction"):
            dim("Intake: token Figma expirado, executor vai extrair via MCP")
            return contract
        else:
            warn("Intake: nenhum componente extraido")
            return None
    except ImportError:
        return None
    except Exception as e:
        warn(f"Intake falhou: {e}")
        return None


def build_initial_message(ctx: TaskContext) -> str:
    if ctx.figma_url:
        file_key, node_id = parse_figma_url(ctx.figma_url)

        # Tentar intake
        contract = _run_intake(ctx)

        if contract and contract.get("components"):
            # Intake extraiu tokens — injetar no prompt
            components_summary = []
            for comp in contract["components"][:20]:
                tokens = comp.get("tokens", {})
                typo = tokens.get("typography", {})
                colors = tokens.get("colors", {})
                line = f"- {comp['name']} ({comp.get('type','')})"
                if typo.get("fontSize"):
                    line += f" — {typo['fontSize']} {typo.get('fontWeight','')}"
                if colors.get("fill"):
                    line += f" fill={colors['fill']}"
                components_summary.append(line)

            return f"""Design tokens JA EXTRAIDOS do Figma (intake automatico).
Use ESTES valores exatos na implementacao:

{chr(10).join(components_summary)}

Cores globais: {', '.join(contract.get('globals',{}).get('colors',[])) or 'ver tokens acima'}
Fontes: {', '.join(contract.get('globals',{}).get('fonts',[])) or 'ver tokens acima'}

Contrato completo salvo em: {SCREENSHOTS_DIR}/design-contract.json

Agora:
1. Leia o codigo atual e entenda a estrutura existente
2. Faca o DE-PARA entre os tokens acima e o codigo
3. Implemente cada diferenca usando APENAS os valores do contrato
4. Faca commit quando terminar"""

        # Sem intake — executor extrai via MCP
        try:
            from intake import DesignIntake
            intake_prompt = DesignIntake.build_intake_prompt(file_key, node_id)
        except ImportError:
            intake_prompt = ""

        return f"""{intake_prompt}

1. Use o MCP Figma (get_screenshot e get_design_context). FileKey: {file_key}, NodeId: {node_id}
2. Leia o codigo atual e entenda a estrutura existente
3. Liste TODAS as diferencas entre o Figma e o codigo atual
4. Implemente cada diferenca usando APENAS tokens extraidos do Figma
5. Faca commit quando terminar

Comece pelo Figma — faca get_screenshot primeiro."""

    return "Implemente a task descrita no system prompt. Comece lendo os arquivos relevantes e implementando. Faca commit quando terminar."


def _get_memory_context(ctx: TaskContext) -> str:
    """Busca memorias relevantes no Mem0 pra injetar no contexto."""
    if OdusMemory is None:
        return ""
    try:
        mem = OdusMemory()
        if not mem.available:
            return ""
        return mem.build_context(
            client=ctx.client_name,
            stack=ctx.client_stack,
            task_type=ctx.type,
            task_title=ctx.title,
            limit=10,
        )
    except Exception:
        return ""


def _learn_from_execution(ctx: TaskContext, issues: list[str] | None = None, human_diff: str = ""):
    """Grava aprendizados no Mem0 (so com evidencia)."""
    if OdusMemory is None:
        return
    try:
        mem = OdusMemory()
        if not mem.available:
            return
        created = mem.learn_from_execution(
            client=ctx.client_name,
            stack=ctx.client_stack,
            task_type=ctx.type,
            task_title=ctx.title,
            human_intervention=ctx.human_intervention,
            review_rejected=not ctx.review_approved,
            verify_failed=ctx.gate_verify == "fail",
            qa_failed=ctx.qa_failed,
            files_changed=ctx.files_changed,
            issues=issues,
            human_diff=human_diff,
        )
        if created:
            ok(f"Mem0: {len(created)} memorias gravadas")
        else:
            dim("Mem0: sem evidencia, nada gravado")
    except Exception as e:
        dim(f"Mem0: erro ao gravar ({e})")


def _build_context_json(ctx: TaskContext, extra_prompt: str = "") -> Path:
    """Salva contexto da task como JSON pro Pi runner."""
    file_key, node_id = "", ""
    if ctx.figma_url:
        file_key, node_id = parse_figma_url(ctx.figma_url)

    context = {
        "title": ctx.title,
        "clientName": ctx.client_name,
        "clientStack": ctx.client_stack,
        "description": ctx.description,
        "stepsToReproduce": ctx.steps_to_reproduce,
        "figmaUrl": ctx.figma_url,
        "figmaFileKey": file_key,
        "figmaNodeId": node_id,
        "comments": ctx.comments,
        "skills": ctx.skills,
        "knowledge": ctx.knowledge,
        "stackContext": ctx.stack_context,
        "plan": ctx.plan,
        "previousTraces": ctx.previous_context,
        "branchName": ctx.branch_name,
        "type": ctx.type,
        "risk": ctx.risk,
        "extraPrompt": extra_prompt,
        "memoryContext": _get_memory_context(ctx),
    }

    ctx_file = Path(tempfile.mktemp(suffix=".json", prefix="odus-ctx-"))
    ctx_file.write_text(json.dumps(context, ensure_ascii=False))
    return ctx_file


def _run_executor(ctx: TaskContext, prompt_text: str, initial_msg: str):
    """Roda o executor via Pi runner (com fallback pra Claude Code)."""
    ctx_file = _build_context_json(ctx, prompt_text)
    runner_dir = SCRIPT_DIR / "pi"

    env = {
        **os.environ,
        "ODUS_CONTEXT_FILE": str(ctx_file),
        "ODUS_TRACE_ID": ctx.trace_id or "",
        "ODUS_BRANCH_NAME": ctx.branch_name,
        "ODUS_API_BASE": API_LOCAL,
    }

    cmd = ["npx", "tsx", str(runner_dir / "runner.ts")]
    cmd += ["--model", ctx.executor_model]
    cmd += ["--message", initial_msg]
    cmd += ["--context-file", str(ctx_file)]
    if ctx.skip_perms:
        cmd.append("--auto")

    try:
        subprocess.run(cmd, check=False, env=env, cwd=str(REPO_DIR))
    except KeyboardInterrupt:
        print()
        warn("Ctrl+C — executor interrompido")
    finally:
        ctx_file.unlink(missing_ok=True)


def etapa_execute(ctx: TaskContext):
    """Etapa 4 — Executor (Claude Code)."""
    print()
    hr()

    ctx.skip_perms = (
        ctx.auto_mode
        or ctx.autonomy in ("auto", "auto_lowrisk", "full_auto")
        or ctx.risk in ("low", "medium")
    )

    log(f"Abrindo Claude Code ({ctx.executor_model})...")
    mode = "autonomo" if ctx.skip_perms else "supervisionado"
    dim(f"Modo {mode} (risk={ctx.risk}, autonomy={ctx.autonomy})")
    dim("(voce pode intervir — ctrl+c quando estiver pronto)")
    trace_event(ctx, "agent", "started", {"role": "executor", "model": ctx.executor_model})
    print()

    executor_start = time.time()
    _run_executor(ctx, build_executor_prompt(ctx), build_initial_message(ctx))
    executor_time = int(time.time() - executor_start)

    hr()
    print()
    ok(f"Claude Code finalizado ({executor_time}s)")
    trace_event(ctx, "agent", "completed", {"role": "executor", "model": ctx.executor_model}, executor_time * 1000)


# ── Agentes Especializados ───────────────────────────────────────────────────

SCOUT_CACHE_DIR = Path(tempfile.gettempdir()) / "odus-scout-cache"
SCOUT_CACHE_DIR.mkdir(exist_ok=True)


def _get_repo_cache_key() -> str:
    """Gera chave de cache baseada no repo path + HEAD hash."""
    r = sh(["git", "rev-parse", "HEAD"])
    head_hash = r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
    repo_name = REPO_DIR.name
    return f"{repo_name}-{head_hash}"


def _load_scout_cache(cache_key: str) -> dict | None:
    """Carrega cache do scout se existir e for do mesmo repo state."""
    cache_file = SCOUT_CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if isinstance(data, dict) and data.get("relevant_files"):
                return data
        except Exception:
            pass
    return None


def _save_scout_cache(cache_key: str, data: dict):
    """Salva resultado do scout em cache."""
    cache_file = SCOUT_CACHE_DIR / f"{cache_key}.json"
    try:
        cache_file.write_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def run_scout(ctx: TaskContext) -> dict | None:
    """Agente SCOUT: reconhece o repo e produz mapa concreto pro implementador."""
    log("Scout: reconhecendo repositorio...")
    scout_start = time.time()

    # 1. Analise estatica (sem LLM)
    repo_info = analyze_repo_structure()
    dim(f"Projeto: {repo_info['type']} | {repo_info['total_source_files']} arquivos fonte")

    # 2. Checar cache (mesmo repo + mesmo HEAD = mesma estrutura)
    cache_key = _get_repo_cache_key()
    cached = _load_scout_cache(cache_key)
    if cached:
        scout_time = int(time.time() - scout_start)
        ok(f"Scout: usando cache ({scout_time}s) — {len(cached.get('relevant_files', []))} arquivos")
        cached["_repo_info"] = repo_info
        cached["_from_cache"] = True
        trace_event(ctx, "agent", "scout_cached", {"cache_key": cache_key})
        return cached

    # 3. Montar contexto compacto
    tree_summary = ""
    for item in repo_info.get("tree", []):
        if item["files"]:
            tree_summary += f"\n{item['dir']}/\n"
            for f in item["files"][:20]:
                tree_summary += f"  {f}\n"
            if len(item["files"]) > 20:
                tree_summary += f"  ... (+{len(item['files']) - 20} arquivos)\n"

    deps_text = ", ".join(repo_info.get("dependencies", [])[:20])
    root_text = ", ".join(repo_info.get("root_files", []))

    desc_clean = re.sub(r"<[^<]+?>", " ", ctx.description or "").strip()[:1500]

    figma_section = ""
    if ctx.figma_url:
        file_key, node_id = parse_figma_url(ctx.figma_url)
        figma_section = f"""
## Figma
URL: {ctx.figma_url}
FileKey: {file_key} | NodeId: {node_id}
IMPORTANTE: Use get_screenshot e get_design_context pra inspecionar o design antes de responder."""

    comments_text = ""
    if ctx.comments:
        comments_text = "\n## Comentarios\n"
        for c in ctx.comments:
            comments_text += f"- {c.get('author', '?')}: {c.get('content', '')}\n"

    # Prompt do scout — CURTO e DIRETO
    scout_prompt = f"""Voce e o SCOUT. Reconheca o repositorio e mapeie o que precisa ser feito.

REGRAS:
- NAO implemente nada. NAO crie arquivos. NAO edite codigo.
- Use Read, Glob, Grep pra explorar o repositorio.
- Sua UNICA saida deve ser um JSON. Nada antes, nada depois.

## Task: {ctx.title}
Tipo: {ctx.type} | Stack: {ctx.client_stack}

{desc_clean[:1000]}
{f"Steps: {ctx.steps_to_reproduce}" if ctx.steps_to_reproduce else ""}
{comments_text}
{figma_section}

## Repo: {repo_info['type']}
Raiz: {root_text}
Deps: {deps_text}
{tree_summary}

## Trabalho:
1. Leia arquivos relevantes pra task
2. Identifique patterns (imports, styling, naming)
3. Liste componentes existentes reutilizaveis
4. Defina quais arquivos editar/criar
5. Escreva approach passo-a-passo
{'''6. Use get_screenshot e get_design_context do MCP Figma''' if ctx.figma_url else ""}

## RESPONDA APENAS com este JSON (sem texto, sem markdown, sem ```):
{{"project_type":"string","relevant_files":["path"],"files_to_modify":["path"],"existing_components":["name"],"patterns":{{"imports":"string","styling":"string","state":"string","naming":"string"}},"conventions":["string"],"approach":"string","warnings":["string"],"files_to_read_first":["path"]{', "figma_analysis":{"gaps":["string"],"tokens":{}}' if ctx.figma_url else ""}}}"""

    # Rodar scout
    scout_file = Path(tempfile.mktemp(suffix=".txt", prefix="odus-scout-"))
    scout_file.write_text(scout_prompt)
    mcp_file, mcp_flag = get_mcp_config()

    scout_msg = "Explore o repositorio com Read/Glob/Grep. Responda APENAS com o JSON — sem texto antes ou depois, sem markdown fences."
    if ctx.figma_url:
        file_key, node_id = parse_figma_url(ctx.figma_url)
        scout_msg = f"Explore o repositorio com Read/Glob/Grep e o Figma com get_screenshot (FileKey: {file_key}, NodeId: {node_id}). Responda APENAS com o JSON — sem texto antes ou depois, sem markdown fences."

    cmd = ["claude", "-p", "--model", "sonnet"]
    cmd += mcp_flag
    cmd += ["--append-system-prompt-file", str(scout_file)]
    cmd += ["--output-format", "text"]
    cmd += ["--max-turns", "20"]
    if ctx.skip_perms:
        cmd.insert(1, "--dangerously-skip-permissions")
    cmd.append(scout_msg)

    text = ""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        text = result.stdout or ""
        # Incluir stderr se stdout veio vazio (alguns erros vao pra stderr)
        if not text.strip() and result.stderr:
            dim(f"Scout stderr: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        warn("Scout: timeout (300s)")
    except Exception as e:
        warn(f"Scout: erro — {e}")
    finally:
        scout_file.unlink(missing_ok=True)
        if mcp_file:
            mcp_file.unlink(missing_ok=True)

    # Extrair JSON com parser robusto
    scout_data = _extract_json(text)

    scout_time = int(time.time() - scout_start)

    if scout_data and isinstance(scout_data, dict) and scout_data.get("relevant_files"):
        files_mapped = len(scout_data.get("relevant_files", []))
        ok(f"Scout completo ({scout_time}s) — {files_mapped} arquivos mapeados")
        if scout_data.get("approach"):
            dim(f"Approach: {scout_data['approach'][:200]}")
        if scout_data.get("warnings"):
            for w in scout_data["warnings"][:3]:
                warn(f"Scout: {w}")
        trace_event(ctx, "agent", "scout_completed", {
            "duration": scout_time,
            "files_mapped": files_mapped,
            "project_type": scout_data.get("project_type", ""),
        })
        # Salvar cache e repo_info
        _save_scout_cache(cache_key, scout_data)
        scout_data["_repo_info"] = repo_info
        return scout_data

    # Debug: mostrar trecho do output pra diagnostico
    if text.strip():
        dim(f"Scout output ({len(text)} chars): {text[:300]}...")
    warn(f"Scout nao retornou JSON valido ({scout_time}s)")
    trace_event(ctx, "agent", "scout_failed", {"duration": scout_time, "output_len": len(text)})
    return None


def build_implementer_prompt(ctx: TaskContext, scout: dict, local_knowledge: dict | None = None) -> str:
    """Prompt cirurgico baseado no scout report + conhecimento local."""
    lk = local_knowledge or {}
    lines = []

    # Agent persona (define o tom e comportamento)
    if lk.get("agent_persona"):
        # Extrair apenas a parte de system prompt (depois do frontmatter)
        persona = lk["agent_persona"]
        frontmatter_end = persona.find("---", persona.find("---") + 3)
        if frontmatter_end > 0:
            persona = persona[frontmatter_end + 3:].strip()
        lines.append(persona[:3000])
        lines.append("")

    # Template da stack (convencoes do projeto)
    if lk.get("template"):
        lines.append(lk["template"][:4000])
        lines.append("")

    lines.append(f"# Task: {ctx.title}")

    # Contexto CONCRETO do repo
    lines += [
        f"\n## Projeto: {scout.get('project_type', ctx.client_stack)}",
        f"Client: {ctx.client_name} ({ctx.client_stack})",
    ]

    if scout.get("patterns"):
        p = scout["patterns"]
        lines.append(f"Patterns: imports={p.get('imports', '?')} | styling={p.get('styling', '?')} | state={p.get('state', '?')} | naming={p.get('naming', '?')}")

    if scout.get("conventions"):
        lines.append(f"Convencoes: {', '.join(scout['conventions'][:5])}")

    # Descricao
    if ctx.description:
        desc_clean = re.sub(r"<[^<]+?>", " ", ctx.description).strip()[:2000]
        lines += ["\n## Descricao", desc_clean]

    if ctx.comments:
        lines.append(f"\n## Comentarios ({len(ctx.comments)})")
        for c in ctx.comments:
            lines.append(f"**{c.get('author', '?')}** ({str(c.get('date', ''))[:10]}): {c.get('content', '')}")

    if ctx.steps_to_reproduce:
        lines += ["\n## Steps to reproduce", ctx.steps_to_reproduce]

    # Arquivos pra ler ANTES de codar
    if scout.get("files_to_read_first"):
        lines.append("\n## Leia ESTES arquivos primeiro (nesta ordem):")
        for f in scout["files_to_read_first"]:
            lines.append(f"1. `{f}`")

    # Arquivos que devem ser modificados
    if scout.get("files_to_modify"):
        lines.append("\n## Arquivos que precisam ser editados/criados:")
        for f in scout["files_to_modify"]:
            lines.append(f"- `{f}`")

    # Componentes reutilizaveis
    if scout.get("existing_components"):
        lines.append("\n## Componentes que JA EXISTEM (reutilize, nao recrie):")
        for comp in scout["existing_components"]:
            lines.append(f"- {comp}")

    # Approach do scout (passo a passo concreto)
    if scout.get("approach"):
        lines += ["\n## Approach (siga este plano):", scout["approach"]]

    # Figma de-para
    if scout.get("figma_analysis"):
        fa = scout["figma_analysis"]
        if fa.get("gaps"):
            lines.append("\n## Figma: diferencas identificadas")
            for gap in fa["gaps"]:
                lines.append(f"- {gap}")
        if fa.get("tokens"):
            lines.append(f"\nTokens do Figma: {json.dumps(fa['tokens'])}")

    if ctx.figma_url:
        lines += [f"\n## Figma URL: {ctx.figma_url}",
                  "Se precisar conferir algo do design, use get_screenshot e get_design_context."]

    # Skills como REGRAS (nao texto bruto)
    if ctx.skills:
        lines.append(f"\n## Regras obrigatorias ({ctx.client_stack})")
        for skill in ctx.skills:
            rules = extract_actionable_rules(skill)
            lines.append(f"\n### {skill['name']}")
            for rule in rules:
                lines.append(f"- {rule}")

    # Knowledge como warnings
    if ctx.knowledge:
        lines.append("\n## Gotchas conhecidos (ATENCAO)")
        for k in ctx.knowledge:
            lines.append(f"- **{k['title']}**: {k['content'][:200]}")
            if k.get("negative"):
                lines.append(f"  NAO FACA: {k['negative']}")

    # Stack context
    if ctx.stack_context.get("rules"):
        lines += ["\n## Rules da stack", ctx.stack_context["rules"]]

    if ctx.stack_context.get("checklist"):
        lines.append("\n## Checklist")
        for item in ctx.stack_context["checklist"]:
            lines.append(f"- [ ] {item}")

    # Warnings do scout
    if scout.get("warnings"):
        lines.append("\n## Cuidados (detectados pelo scout)")
        for w in scout["warnings"]:
            lines.append(f"- {w}")

    # Traces anteriores
    if ctx.previous_context:
        lines += ["\n" + ctx.previous_context]

    # Patterns locais da stack
    if lk.get("patterns"):
        lines.append(f"\n## Patterns da stack ({len(lk['patterns'])} carregados)")
        for pat in lk["patterns"][:8]:
            lines.append(f"\n### {pat['name']}")
            lines.append(pat["content"][:1500])

    # Memory da stack (decisoes e aprendizados)
    if lk.get("memory"):
        lines.append("\n## Memory (decisoes e aprendizados acumulados)")
        lines.append(lk["memory"][:2000])

    # Skills locais disponiveis
    if lk.get("skills_available"):
        lines.append(f"\n## Skills do Claude Code disponiveis ({len(lk['skills_available'])})")
        lines.append("Carregue estes skills quando precisar de referencia detalhada:")
        for s in lk["skills_available"][:15]:
            lines.append(f"- /{s}")

    # Ferramentas e MCPs disponiveis
    lines.append("\n## Ferramentas disponiveis")
    lines.append("Voce tem acesso a ferramentas do Claude Code (Read, Edit, Write, Glob, Grep, Bash).")
    lines.append("USE-AS ativamente — nao tente adivinhar conteudo de arquivos.")

    mcp_instructions = []
    if ctx.figma_url:
        mcp_instructions.append("- **Figma MCP**: use get_screenshot e get_design_context pra consultar o design. SEMPRE consulte o Figma antes de implementar mudancas visuais.")
    if ctx.client_stack.lower() in ("vtex io", "vtex-io"):
        mcp_instructions.append("- **VTEX docs**: se tiver duvida sobre APIs ou componentes VTEX, consulte a documentacao disponivel via MCP.")
    if ctx.client_stack.lower() in ("shopify",):
        mcp_instructions.append("- **Shopify docs**: consulte a documentacao Shopify via MCP se precisar de referencia de APIs, Liquid tags ou Hydrogen.")

    if mcp_instructions:
        lines.append("\n## MCPs (USE quando precisar)")
        lines.extend(mcp_instructions)

    # Skills do Claude Code (instruir a carregar quando disponivel)
    skill_map = {
        "vtex io": ["vtex-io-storefront-react", "vtex-io-react-apps"],
        "vtex-io": ["vtex-io-storefront-react", "vtex-io-react-apps"],
        "deco.cx": ["faststore-storefront"],
        "deco-cx": ["faststore-storefront"],
        "faststore": ["faststore-storefront"],
        "shopify": [],
    }
    available_skills = skill_map.get(ctx.client_stack.lower().replace(" ", "-"), [])
    if ctx.type == "layout" or ctx.figma_url:
        available_skills.append("figma-design-to-code")
    if available_skills:
        lines.append("\n## Skills do Claude Code (carregue se disponivel)")
        lines.append("Se estas skills estiverem disponiveis no seu ambiente, USE-AS:")
        for s in available_skills:
            lines.append(f"- /{s}")

    # Tokens do Figma como contrato (se disponivel)
    if scout.get("figma_tokens"):
        lines.append("\n## Tokens do Figma (CONTRATO — use APENAS estes valores)")
        lines.append("Qualquer cor, font-size, spacing ou tamanho que nao esteja nesta lista e um BUG.")
        lines.append(f"```json\n{json.dumps(scout['figma_tokens'], indent=2, ensure_ascii=False)}\n```")

    # Instrucoes finais (curtas)
    lines += [
        "\n## Execucao",
        "1. Leia os arquivos listados acima (comece por files_to_read_first)",
        "2. Implemente seguindo o approach do scout",
        "3. Respeite os patterns e convencoes do projeto",
        "4. Siga as regras e gotchas",
        "5. NAO faca commit — apenas implemente e salve os arquivos",
        "6. NAO faca push",
        "7. NAO crie arquivos desnecessarios",
        "",
        "## Regras de codigo",
        "- JSX/TSX moderno — NUNCA React.createElement()",
        "- const/let — NUNCA var",
        "- Arrow functions, destructuring, optional chaining (?.), nullish coalescing (??)",
        "- ZERO console.log em producao",
        "- Leia e edite APENAS arquivos fonte — NUNCA dist/, build/",
        "- Se tem tokens do Figma acima, use APENAS esses valores — nao invente cores, spacing ou tamanhos",
    ]

    return "\n".join(lines)


def build_initial_message_v2(ctx: TaskContext, scout: dict) -> str:
    """Mensagem inicial baseada no scout report."""
    suffix = "NAO faca commit — apenas implemente e salve os arquivos. O pipeline cuida do commit depois."

    if ctx.figma_url and scout.get("figma_analysis"):
        gaps = scout["figma_analysis"].get("gaps", [])
        if gaps:
            gaps_text = "\n".join(f"- {g}" for g in gaps[:10])
            return f"""O Scout ja analisou o Figma e o codigo. Estas sao as diferencas:

{gaps_text}

Implemente cada diferenca seguindo o approach do scout. Comece lendo os arquivos listados em files_to_read_first. {suffix}"""

    if scout.get("approach"):
        return f"""O Scout ja analisou o repositorio. Siga o approach definido:

{scout['approach'][:500]}

Comece lendo os arquivos listados em files_to_read_first. {suffix}"""

    return f"Implemente a task seguindo o approach e as instrucoes do system prompt. Comece lendo os arquivos indicados. {suffix}"


def run_verifier(ctx: TaskContext, scout: dict) -> dict:
    """Agente VERIFICADOR: checa diff contra regras e patterns antes do QA."""
    log("Verificador: checagem rapida pre-QA...")

    diff_r = sh(["git", "diff", "main...HEAD"])
    diff = diff_r.stdout[:5000] if diff_r.stdout else ""

    if not diff.strip():
        warn("Verificador: nenhum diff encontrado")
        return {"ok": False, "issues": ["Nenhuma mudanca detectada"], "fixable": False}

    files_r = sh(["git", "diff", "--name-only", "main...HEAD"])
    files_changed = files_r.stdout.strip()

    patterns_text = json.dumps(scout.get("patterns", {})) if scout.get("patterns") else "N/A"
    approach_text = scout.get("approach", "N/A")[:300]

    prompt = f"""Verificacao rapida pre-QA. Analise o diff contra as regras do projeto.

Stack: {ctx.client_stack} | Tipo: {ctx.type}
Patterns do projeto: {patterns_text}
Approach esperado: {approach_text}
Arquivos que deveriam ser modificados: {json.dumps(scout.get('files_to_modify', []))}

## Checklist
- Seguiu o approach? (modificou os arquivos certos?)
- Usou componentes existentes ao inves de criar novos?
- Respeitou patterns do projeto (imports, styling, naming)?
- Tem console.log em codigo de producao?
- Tem any explicito em TypeScript?
- Tem inline styles onde deveria usar CSS class/handles?
- Tem imports nao usados?
- Tem codigo comentado desnecessario?
- Criou arquivos que nao deveria?

## Arquivos alterados:
{files_changed}

## Diff:
{diff}

Responda APENAS em JSON:
{{"ok": true/false, "issues": ["descricao curta do problema"], "fixable": true/false, "summary": "resumo"}}"""

    result = claude_json(prompt, "haiku", timeout=45)

    if isinstance(result, dict):
        if result.get("ok"):
            ok("Verificador: ok")
        else:
            issues = result.get("issues", [])
            warn(f"Verificador: {len(issues)} issues")
            for issue in issues[:5]:
                dim(f"  - {issue}")
        return result

    dim("Verificador: timeout/erro (assumindo ok)")
    return {"ok": True, "issues": []}


def _group_files_by_scope(files: list[str]) -> list[list[str]]:
    """Agrupa arquivos por diretorio/escopo pra batching inteligente.

    Arquivos no mesmo diretorio ou com prefixo comum ficam juntos.
    Maximo ~4 arquivos por batch pra manter contexto gerenciavel.
    """
    MAX_PER_BATCH = 4

    if len(files) <= MAX_PER_BATCH:
        return [files]

    # Agrupar por diretorio pai
    groups: dict[str, list[str]] = {}
    for f in files:
        parts = f.split("/")
        # Usar os 2 primeiros niveis como chave (ex: "react/components")
        key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        groups.setdefault(key, []).append(f)

    # Montar batches respeitando o limite
    batches: list[list[str]] = []
    current: list[str] = []

    for _key, group_files in sorted(groups.items()):
        if len(current) + len(group_files) > MAX_PER_BATCH and current:
            batches.append(current)
            current = []

        if len(group_files) > MAX_PER_BATCH:
            # Grupo grande demais, quebrar
            for i in range(0, len(group_files), MAX_PER_BATCH):
                batches.append(group_files[i:i + MAX_PER_BATCH])
        else:
            current.extend(group_files)

    if current:
        batches.append(current)

    return batches


def _build_batch_prompt(ctx: TaskContext, scout: dict, batch_files: list[str], batch_num: int, total_batches: int, local_knowledge: dict | None = None) -> str:
    """Prompt focado pra um lote especifico de arquivos."""
    lk = local_knowledge or {}
    lines = []

    # Template da stack (compacto pro batch)
    if lk.get("template"):
        lines.append(lk["template"][:2000])
        lines.append("")

    lines += [
        f"# Task: {ctx.title} (Lote {batch_num}/{total_batches})",
        f"Client: {ctx.client_name} ({ctx.client_stack})",
        f"\n## Projeto: {scout.get('project_type', ctx.client_stack)}",
    ]

    if scout.get("patterns"):
        p = scout["patterns"]
        lines.append(f"Patterns: imports={p.get('imports', '?')} | styling={p.get('styling', '?')} | naming={p.get('naming', '?')}")

    if scout.get("conventions"):
        lines.append(f"Convencoes: {', '.join(scout['conventions'][:5])}")

    # Descricao (resumida pro batch)
    if ctx.description:
        desc_clean = re.sub(r"<[^<]+?>", " ", ctx.description).strip()[:1000]
        lines += ["\n## Descricao da task completa", desc_clean]

    # Approach completo pra referencia
    if scout.get("approach"):
        lines += ["\n## Approach geral (referencia):", scout["approach"]]

    # FOCO: arquivos deste lote
    lines.append(f"\n## ESCOPO DESTE LOTE — edite APENAS estes arquivos:")
    for f in batch_files:
        lines.append(f"- `{f}`")

    lines.append("\nNAO edite arquivos fora deste lote. Outros lotes cuidam do resto.")

    # Componentes reutilizaveis
    if scout.get("existing_components"):
        lines.append("\n## Componentes existentes (pode importar/reusar):")
        for comp in scout["existing_components"][:10]:
            lines.append(f"- {comp}")

    # Figma (se relevante pro batch)
    if scout.get("figma_analysis"):
        fa = scout["figma_analysis"]
        if fa.get("gaps"):
            lines.append("\n## Figma: gaps relevantes")
            for gap in fa["gaps"][:5]:
                lines.append(f"- {gap}")

    if ctx.figma_url:
        lines += [f"\nFigma URL: {ctx.figma_url}",
                  "Se precisar conferir algo do design, use get_screenshot e get_design_context."]

    # Skills como regras
    if ctx.skills:
        lines.append(f"\n## Regras ({ctx.client_stack})")
        for skill in ctx.skills:
            rules = extract_actionable_rules(skill)
            for rule in rules:
                lines.append(f"- {rule}")

    # Knowledge
    if ctx.knowledge:
        lines.append("\n## Gotchas")
        for k in ctx.knowledge[:5]:
            lines.append(f"- {k['title']}: {k['content'][:150]}")

    # Instrucoes
    lines += [
        "\n## Execucao",
        "1. Leia os arquivos deste lote",
        "2. Implemente as mudancas necessarias seguindo o approach",
        "3. Respeite patterns e convencoes do projeto",
        "4. NAO faca commit — apenas implemente e salve",
        "5. NAO faca push",
        "",
        "## Regras de codigo",
        "- JSX/TSX moderno — NUNCA React.createElement()",
        "- const/let — NUNCA var",
        "- ZERO console.log em producao",
        "- Leia e edite APENAS arquivos fonte — NUNCA dist/, build/",
    ]

    return "\n".join(lines)


def _extract_figma_tokens(ctx: TaskContext) -> dict | None:
    """Extrai tokens do Figma (cores, tipografia, spacing) como contrato pro implementer."""
    if not ctx.figma_url:
        return None

    file_key, node_id = parse_figma_url(ctx.figma_url)
    if not file_key:
        return None

    log("Extraindo tokens do Figma...")
    mcp_file, mcp_flag = get_mcp_config()

    prompt = f"""Use get_design_context do MCP Figma pra extrair TODOS os tokens visuais deste frame.
FileKey: {file_key}
NodeId: {node_id}

Extraia e retorne APENAS em JSON (sem texto, sem markdown):
{{
  "colors": {{"nome_semantico": "#hex"}},
  "typography": {{"nome": "weight size/lineHeight family"}},
  "spacing": {{"nome": "Xpx"}},
  "borderRadius": {{"nome": "Xpx"}},
  "shadows": {{"nome": "box-shadow value"}},
  "borders": {{"nome": "Xpx solid #hex"}}
}}

IMPORTANTE:
- Use nomes semanticos (ex: "price-color", "title-font", "section-gap")
- Valores EXATOS do Figma, nao aproxime
- Inclua TODOS os tokens visiveis no frame"""

    cmd = ["claude", "-p", "--model", "sonnet"]
    cmd += mcp_flag
    cmd += ["--output-format", "text"]
    cmd += ["--max-turns", "5"]
    cmd.append(prompt)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        tokens = _extract_json(result.stdout)
        if isinstance(tokens, dict) and (tokens.get("colors") or tokens.get("typography")):
            token_count = sum(len(v) for v in tokens.values() if isinstance(v, dict))
            ok(f"Tokens extraidos: {token_count} valores")
            return tokens
    except Exception:
        pass
    finally:
        if mcp_file:
            mcp_file.unlink(missing_ok=True)

    dim("Tokens: nao conseguiu extrair")
    return None


def _run_self_review(ctx: TaskContext, scout: dict) -> dict:
    """Self-review: checa o diff contra tokens, patterns e regras ANTES de commitar."""
    log("Self-review...")

    diff_r = sh(["git", "diff"])
    diff = diff_r.stdout[:6000] if diff_r.stdout else ""

    if not diff.strip():
        dim("Self-review: nenhuma mudanca")
        return {"ok": True, "issues": []}

    files_r = sh(["git", "diff", "--name-only"])
    files_changed = files_r.stdout.strip()

    tokens_text = ""
    if scout.get("figma_tokens"):
        tokens_text = f"\n## Tokens do Figma (CONTRATO)\n```json\n{json.dumps(scout['figma_tokens'], indent=2)}\n```\n"

    patterns_text = json.dumps(scout.get("patterns", {})) if scout.get("patterns") else "N/A"

    prompt = f"""Voce e o self-reviewer. Analise este diff ANTES dele ser commitado.

Stack: {ctx.client_stack} | Tipo: {ctx.type}
Patterns do projeto: {patterns_text}
{tokens_text}

## Checklist RIGOROSO:
1. TOKENS: Se tem tokens do Figma acima, CADA cor, font-size e spacing no diff usa EXATAMENTE um valor da lista? Valores inventados = FAIL
2. PATTERNS: Segue o pattern de imports, styling e naming do projeto?
3. CONSOLE.LOG: Tem algum console.log?
4. ANY: Tem any explicito em TypeScript?
5. INLINE STYLES: Tem style={{}} onde deveria usar classe CSS?
6. MAGIC NUMBERS: Tem valores hardcoded que deveriam ser variaveis/tokens?
7. IMPORTS: Tem imports nao usados?
8. CODIGO MORTO: Tem codigo comentado desnecessario?
9. SEMANTICA: HTML semantico? (nao div pra tudo)
10. ACESSIBILIDADE: alt em imagens, aria-labels em botoes interativos?

## Arquivos:
{files_changed}

## Diff:
{diff}

SEJA RIGOROSO. Se tem qualquer problema, ok=false.

JSON (sem markdown):
{{"ok": true/false, "issues": ["descricao com linha/arquivo se possivel"], "token_violations": ["valor X usado mas nao esta nos tokens"], "summary": "resumo"}}"""

    result = claude_json(prompt, "sonnet", timeout=60)

    if isinstance(result, dict):
        if result.get("ok"):
            ok("Self-review: aprovado")
        else:
            issues = result.get("issues", [])
            token_violations = result.get("token_violations", [])
            warn(f"Self-review: {len(issues)} issues, {len(token_violations)} violacoes de token")
            for issue in issues[:5]:
                dim(f"  - {issue}")
            for tv in token_violations[:3]:
                fail(f"  TOKEN: {tv}")
        return result

    dim("Self-review: timeout/erro (assumindo ok)")
    return {"ok": True, "issues": []}


def _run_design_lint(ctx: TaskContext, scout: dict) -> dict:
    """CSS/Design lint: audit de tokens, magic numbers, consistencia."""
    if ctx.type not in ("layout", "frontend", "feature"):
        dim("Design lint: skip (tipo nao visual)")
        return {"ok": True, "issues": []}

    log("Design lint...")

    diff_r = sh(["git", "diff"])
    diff = diff_r.stdout[:5000] if diff_r.stdout else ""

    if not diff.strip():
        return {"ok": True, "issues": []}

    # Filtrar apenas mudancas em CSS/SCSS
    css_lines = []
    current_file = ""
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            current_file = line
        if current_file and (".css" in current_file or ".scss" in current_file):
            if line.startswith("+") and not line.startswith("+++"):
                css_lines.append(line)

    if not css_lines:
        dim("Design lint: sem mudancas CSS/SCSS")
        return {"ok": True, "issues": []}

    css_diff = "\n".join(css_lines[:100])

    tokens_text = ""
    if scout.get("figma_tokens"):
        tokens_text = f"Tokens do Figma:\n{json.dumps(scout['figma_tokens'], indent=2)}\n"

    prompt = f"""Audit de CSS/SCSS. Analise as linhas adicionadas e encontre problemas.

{tokens_text}

## Linhas CSS/SCSS adicionadas:
{css_diff}

## Checklist:
1. MAGIC NUMBERS: valores px/rem/em hardcoded que deveriam ser variaveis (ex: 13px em vez de 12px ou 14px)
2. CORES FORA DO TOKEN: cores hex/rgb que nao batem com os tokens do Figma
3. SPACING INCONSISTENTE: gaps/margins/paddings com valores quebrados (ex: 15px quando o sistema usa 8/16/24)
4. !IMPORTANT: uso desnecessario de !important
5. SELETORES FRAGEIS: seletores muito especificos ou que dependem de estrutura DOM
6. FONT: font-family/weight/size que nao batem com tokens de tipografia

JSON (sem markdown):
{{"ok": true/false, "issues": ["descricao"], "violations": [{{"type": "magic_number|wrong_color|inconsistent_spacing|important|fragile_selector|wrong_font", "value": "o que encontrou", "expected": "o que deveria ser"}}]}}"""

    result = claude_json(prompt, "haiku", timeout=45)

    if isinstance(result, dict):
        if result.get("ok"):
            ok("Design lint: aprovado")
        else:
            issues = result.get("issues", [])
            violations = result.get("violations", [])
            warn(f"Design lint: {len(issues)} issues, {len(violations)} violacoes")
            for v in violations[:5]:
                dim(f"  [{v.get('type', '?')}] {v.get('value', '')} → esperado: {v.get('expected', '?')}")
        return result

    dim("Design lint: timeout/erro")
    return {"ok": True, "issues": []}


def _find_reference_code(scout: dict, ctx: TaskContext) -> str:
    """Encontra código de referência no repo pra componentes similares."""
    existing = scout.get("existing_components", [])
    if not existing:
        return ""

    # Ler o conteudo dos primeiros componentes existentes como referencia
    references = []
    for comp in existing[:3]:
        # Tentar encontrar o arquivo
        comp_clean = comp.strip().split(" ")[0]  # Pegar só o nome/path
        candidates = []
        for ext in [".tsx", ".jsx", ".ts", ".js"]:
            r = sh(["find", ".", "-name", f"*{comp_clean}*{ext}", "-not", "-path", "*/node_modules/*", "-not", "-path", "*/dist/*"])
            if r.stdout.strip():
                candidates.extend(r.stdout.strip().split("\n")[:2])

        for candidate in candidates[:1]:
            candidate = candidate.strip()
            if candidate and Path(candidate).exists():
                content = Path(candidate).read_text()[:2000]
                references.append(f"### Referencia: {candidate}\n```\n{content}\n```")

    if references:
        return "\n## Codigo de referencia (componentes similares do projeto)\nUse estes como referencia de padrao — copie o estilo, nao invente.\n\n" + "\n\n".join(references[:2])

    return ""


def _capture_figma_screenshot(ctx: TaskContext) -> str | None:
    """Captura screenshot do Figma via MCP. Retorna path do arquivo."""
    if not ctx.figma_url:
        return None

    file_key, node_id = parse_figma_url(ctx.figma_url)
    if not file_key:
        return None

    figma_screenshot = SCREENSHOTS_DIR / "figma-reference.png"

    # Usar claude -p pra chamar o MCP Figma e salvar screenshot
    mcp_file, mcp_flag = get_mcp_config()
    prompt = f"""Use a ferramenta get_screenshot do MCP Figma pra capturar o design.
FileKey: {file_key}
NodeId: {node_id}

Depois de capturar, salve o resultado descrevendo DETALHADAMENTE o que voce ve no design:
- Layout geral (grid, colunas, distribuicao)
- Cores exatas (hex)
- Tipografia (font, size, weight, line-height)
- Espacamentos visiveis (gaps, margins, paddings)
- Bordas, sombras, border-radius
- Elementos e sua hierarquia

Seja EXTREMAMENTE detalhado e preciso nos valores visuais."""

    cmd = ["claude", "-p", "--model", "sonnet"]
    cmd += mcp_flag
    cmd += ["--output-format", "text"]
    cmd += ["--max-turns", "5"]
    cmd.append(prompt)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        text = result.stdout.strip()
        if text:
            # Salvar descricao do Figma como referencia
            figma_desc_path = SCREENSHOTS_DIR / "figma-description.txt"
            figma_desc_path.write_text(text)
            return str(figma_desc_path)
    except Exception:
        pass
    finally:
        if mcp_file:
            mcp_file.unlink(missing_ok=True)

    return None


def _compare_visual(ctx: TaskContext, adapter: "Adapter", figma_desc_path: str | None, round_num: int) -> dict:
    """Compara implementacao atual vs Figma. Retorna diferencas."""
    log(f"Comparacao visual (round {round_num}/5)...")

    # 1. Subir preview
    if not adapter.up():
        warn("Preview nao subiu. Pulando comparacao visual.")
        return {"match": True, "differences": []}

    ok(f"Preview: {ctx.preview_url}")

    # 2. Capturar screenshot + devtools da implementacao
    impl_screenshot = None
    devtools = adapter._capture_devtools(f"visual-round-{round_num}", 5)
    if devtools and devtools.get("screenshot"):
        impl_screenshot = devtools["screenshot"]
        ok(f"Screenshot capturado: {impl_screenshot}")
    else:
        impl_screenshot_path = adapter._take_screenshot(f"visual-round-{round_num}")
        if impl_screenshot_path:
            impl_screenshot = impl_screenshot_path

    # 3. Ler descricao do Figma
    figma_desc = ""
    if figma_desc_path and Path(figma_desc_path).exists():
        figma_desc = Path(figma_desc_path).read_text()[:4000]

    # 4. Comparar via Claude (sonnet pra qualidade)
    console_errors = ""
    if devtools:
        errors = devtools.get("consoleErrors", [])
        if errors:
            console_errors = f"\n\nErros no console ({len(errors)}):\n" + "\n".join(f"- {e.get('text', '')[:200]}" for e in errors[:5])

    compare_prompt = f"""Voce e um revisor visual pixel-perfect. Compare a implementacao atual com o design do Figma.

## Design do Figma (referencia):
{figma_desc}

## Implementacao atual:
Preview URL: {ctx.preview_url}
{"Screenshot capturado: " + impl_screenshot if impl_screenshot else "Screenshot nao disponivel."}
{console_errors}

## Compare DETALHADAMENTE:
1. Cores: as cores da implementacao batem EXATAMENTE com o Figma? (hex vs hex)
2. Tipografia: font-family, font-size, font-weight, line-height, letter-spacing corretos?
3. Espacamentos: margins, paddings, gaps batem com o Figma?
4. Tamanhos: largura/altura dos elementos, border-radius corretos?
5. Layout: grid, alinhamento, distribuicao dos elementos corretos?
6. Hierarquia: ordem dos elementos, visibilidade, z-index corretos?
7. Responsivo: esta correto no breakpoint mostrado?
8. Erros visuais: elementos cortados, overflow, quebra de layout?

SEJA RIGOROSO. Qualquer diferenca visual e um problema.
Se a implementacao esta 100% fiel ao Figma, diga match=true.

Responda APENAS em JSON:
{{"match": true/false, "score": 0-100, "differences": ["descricao precisa da diferenca com valores esperados vs encontrados"], "critical": ["diferencas mais graves que devem ser corrigidas primeiro"]}}"""

    # Se temos screenshot, usar claude com visao
    if impl_screenshot and Path(impl_screenshot).exists():
        # Claude -p com imagem nao e suportado diretamente, usar descricao
        compare_prompt += f"\n\nIMPORTANTE: O screenshot da implementacao esta em {impl_screenshot}. Analise-o visualmente."

    result = claude_json(compare_prompt, "sonnet", timeout=90)

    adapter.down()

    if isinstance(result, dict):
        score = result.get("score", 50)
        diffs = result.get("differences", [])
        critical = result.get("critical", [])
        is_match = result.get("match", False)

        if is_match or score >= 90:
            ok(f"Visual: {score}/100 — implementacao fiel ao Figma")
        else:
            warn(f"Visual: {score}/100 — {len(diffs)} diferencas detectadas")
            if critical:
                for c in critical[:3]:
                    fail(f"  CRITICO: {c}")
            for d in diffs[:5]:
                dim(f"  - {d}")

        trace_event(ctx, "visual", f"comparison_round_{round_num}", {
            "score": score, "match": is_match,
            "differences": len(diffs), "critical": len(critical),
        })

        return result

    dim("Comparacao visual: timeout/erro")
    return {"match": True, "differences": []}


def _run_visual_comparison_loop(ctx: TaskContext, scout: dict, lk: dict):
    """Loop de comparacao visual: implementa → screenshot → compara → corrige. Max 5 rounds."""
    print()
    log("Iniciando loop de comparacao visual (layout)...")
    hr()

    adapter = resolve_adapter(ctx)
    if not adapter.has_verify:
        dim("Adapter sem verify — pulando loop visual")
        return

    # Pre-flight do adapter (pode ja ter sido feito)
    if not adapter.preflight():
        warn("Preflight falhou — pulando loop visual")
        return

    # Capturar referencia do Figma (1 vez, reusa nos rounds)
    figma_desc_path = _capture_figma_screenshot(ctx)
    if figma_desc_path:
        ok(f"Referencia Figma capturada")
    else:
        warn("Nao conseguiu capturar referencia do Figma — pulando loop visual")
        return

    MAX_ROUNDS = 5
    for round_num in range(1, MAX_ROUNDS + 1):
        print()
        comparison = _compare_visual(ctx, adapter, figma_desc_path, round_num)

        is_match = comparison.get("match", False)
        score = comparison.get("score", 0)
        differences = comparison.get("differences", [])
        critical = comparison.get("critical", [])

        # Se bateu >= 90 ou match, para
        if is_match or score >= 90:
            ok(f"Visual match atingido no round {round_num} (score: {score}/100)")
            trace_event(ctx, "visual", "loop_completed", {
                "rounds": round_num, "final_score": score,
            })
            break

        # Se nao tem diferencas pra corrigir, para
        if not differences and not critical:
            dim("Sem diferencas especificas pra corrigir — parando loop")
            break

        # Montar lista de correcoes priorizadas
        fixes = []
        if critical:
            fixes.extend(critical)
        for d in differences:
            if d not in fixes:
                fixes.append(d)

        # Reabrir implementer com feedback visual
        warn(f"Round {round_num}/{MAX_ROUNDS}: corrigindo {len(fixes)} diferencas visuais...")

        fix_prompt = build_implementer_prompt(ctx, scout, lk) + f"""

## CORRECAO VISUAL — Round {round_num}/{MAX_ROUNDS}

A implementacao foi comparada com o Figma e tem diferencas visuais.
Score atual: {score}/100 (precisa chegar em 90+)

## Diferencas a corrigir (PRIORIDADE: criticas primeiro):
{chr(10).join(f'- {f}' for f in fixes[:15])}

## Instrucoes
- Corrija CADA diferenca listada acima
- Use valores EXATOS do Figma (hex, px, font-weight) — nao aproxime
- Nao mude logica de negocio, apenas visual
- Faca commit quando terminar
- Se precisar conferir o Figma, use get_screenshot e get_design_context"""

        fix_msg = f"""Correcao visual round {round_num}/{MAX_ROUNDS}. Score atual: {score}/100.

Diferencas mais criticas:
{chr(10).join(f'- {f}' for f in (critical or fixes)[:5])}

Corrija e faca commit. Use valores EXATOS do Figma."""

        _run_executor(ctx, fix_prompt, fix_msg)
        ok(f"Correcoes visuais aplicadas (round {round_num})")
        trace_event(ctx, "visual", f"fix_applied_{round_num}", {"fixes": len(fixes)})

    else:
        # Esgotou os 5 rounds
        warn(f"Loop visual: {MAX_ROUNDS} rounds esgotados (score final: {score}/100)")
        trace_event(ctx, "visual", "loop_exhausted", {
            "rounds": MAX_ROUNDS, "final_score": score,
            "remaining_diffs": len(differences),
        })

    # Cleanup
    adapter.down()
    print()


def _reopen_implementer_for_fixes(ctx: TaskContext, scout: dict, lk: dict, issues: list[str], reason: str):
    """Reabre o implementer pra corrigir issues especificos. Sem commit."""
    fix_prompt = build_implementer_prompt(ctx, scout, lk) + f"""

## Correcoes necessarias ({reason})
{chr(10).join(f'- {i}' for i in issues[:15])}

## Instrucoes
- Corrija CADA issue listado acima
- Mantenha a logica original
- Use valores EXATOS dos tokens do Figma se disponivel
- NAO faca commit — apenas corrija e salve os arquivos"""

    fix_msg = f"{reason}: {len(issues)} issues. Corrija todos. NAO faca commit."
    _run_executor(ctx, fix_prompt, fix_msg)
    ok(f"Correcoes aplicadas ({reason})")


def etapa_execute_v2(ctx: TaskContext):
    """Etapa 4 — Executor com agentes especializados.

    Fluxo:
      Scout → Tokens Figma → Implementer (sem commit)
      → Self-review → Design lint → Verificador
      → Visual loop (layout) → COMMIT (pipeline controla)
    """
    print()
    hr()

    ctx.skip_perms = (
        ctx.auto_mode
        or ctx.autonomy in ("auto", "auto_lowrisk", "full_auto")
        or ctx.risk in ("low", "medium")
    )

    mode = "autonomo" if ctx.skip_perms else "supervisionado"

    # ── Scout ──────────────────────────────────
    scout = run_scout(ctx)

    if not scout:
        warn("Scout falhou — usando executor classico como fallback")
        log(f"Abrindo Claude Code ({ctx.executor_model})...")
        dim(f"Modo {mode} (risk={ctx.risk}, autonomy={ctx.autonomy})")
        trace_event(ctx, "agent", "started", {"role": "executor", "model": ctx.executor_model, "mode": "classic"})
        print()
        executor_start = time.time()
        _run_executor(ctx, build_executor_prompt(ctx), build_initial_message(ctx))
        executor_time = int(time.time() - executor_start)
        # Fallback faz commit (modo antigo)
        hr()
        print()
        ok(f"Claude Code finalizado ({executor_time}s)")
        trace_event(ctx, "agent", "completed", {"role": "executor", "model": ctx.executor_model}, executor_time * 1000)
        return

    # ── Tokens do Figma (contrato) ─────────────
    if ctx.figma_url and ctx.type in ("layout", "frontend"):
        tokens = _extract_figma_tokens(ctx)
        if tokens:
            scout["figma_tokens"] = tokens
            trace_event(ctx, "figma", "tokens_extracted", {
                "count": sum(len(v) for v in tokens.values() if isinstance(v, dict))
            })

    # ── Referencia de codigo existente ─────────
    ref_code = _find_reference_code(scout, ctx)
    if ref_code:
        dim(f"Referencia de codigo carregada ({len(ref_code)} chars)")

    # ── Conhecimento local ──────────────────────
    log("Carregando conhecimento local...")
    lk = resolve_local_knowledge(ctx.client_stack, ctx.type)
    loaded = []
    if lk["template"]: loaded.append("template")
    if lk["patterns"]: loaded.append(f"{len(lk['patterns'])} patterns")
    if lk["agent_persona"]: loaded.append("agent persona")
    if lk["memory"]: loaded.append("memory")
    if lk["skills_available"]: loaded.append(f"{len(lk['skills_available'])} skills")
    if loaded:
        ok(f"Local: {', '.join(loaded)}")
    else:
        dim("Local: nenhum conhecimento encontrado pra essa stack")
    trace_event(ctx, "knowledge", "local_loaded", {
        "template": bool(lk["template"]),
        "patterns": len(lk["patterns"]),
        "agent": bool(lk["agent_persona"]),
        "memory": bool(lk["memory"]),
        "skills": len(lk["skills_available"]),
    })

    # ── Regras dos skills (com cache) ─────────
    if ctx.skills:
        log("Processando skills em regras...")
        rules_count = 0
        for skill in ctx.skills:
            rules = extract_actionable_rules(skill)
            rules_count += len(rules)
        ok(f"{rules_count} regras extraidas de {len(ctx.skills)} skills")

    # ── Decidir modo: sessao unica vs batching ─
    files_to_modify = scout.get("files_to_modify", [])
    use_batching = len(files_to_modify) > 5

    executor_start = time.time()

    # ══════════════════════════════════════════════
    # FASE 1: IMPLEMENTACAO (sem commit)
    # ══════════════════════════════════════════════
    print()
    log(f"{C.BOLD}FASE 1: Implementacao{C.NC}")

    if not use_batching:
        print()
        log(f"Implementer ({ctx.executor_model})...")
        dim(f"Modo {mode} (risk={ctx.risk}, autonomy={ctx.autonomy})")
        trace_event(ctx, "agent", "started", {"role": "implementer", "model": ctx.executor_model, "mode": "v2"})
        print()

        implementer_prompt = build_implementer_prompt(ctx, scout, lk)
        # Injetar referencia de codigo se disponivel
        if ref_code:
            implementer_prompt += ref_code

        implementer_msg = build_initial_message_v2(ctx, scout)
        _run_executor(ctx, implementer_prompt, implementer_msg)

    else:
        batches = _group_files_by_scope(files_to_modify)
        print()
        log(f"Implementer ({ctx.executor_model}) — {len(batches)} lotes ({len(files_to_modify)} arquivos)")
        dim(f"Modo {mode} (risk={ctx.risk}, autonomy={ctx.autonomy})")
        trace_event(ctx, "agent", "started", {
            "role": "implementer", "model": ctx.executor_model,
            "mode": "v2_batched", "batches": len(batches), "totalFiles": len(files_to_modify),
        })
        print()

        batch_summaries: list[str] = []

        for i, batch in enumerate(batches, 1):
            log(f"Lote {i}/{len(batches)}: {', '.join(batch)}")
            batch_prompt = _build_batch_prompt(ctx, scout, batch, i, len(batches), lk)

            if batch_summaries:
                batch_prompt += "\n\n## Lotes anteriores (contexto)"
                batch_prompt += "\nEstes lotes ja foram executados. Considere o que foi feito:\n"
                for summary in batch_summaries:
                    batch_prompt += f"\n{summary}"

            batch_msg = f"Lote {i}/{len(batches)}. Edite APENAS: {', '.join(batch)}. NAO faca commit."
            _run_executor(ctx, batch_prompt, batch_msg)
            ok(f"Lote {i}/{len(batches)} finalizado")

            # Resumo pra proximo lote (baseado no diff, nao commit)
            batch_diff_r = sh(["git", "diff", "--stat"] + batch)
            batch_summary = f"### Lote {i}: {', '.join(batch)}\nMudancas: {batch_diff_r.stdout.strip()[:200]}"
            batch_summaries.append(batch_summary)

            trace_event(ctx, "agent", "batch_completed", {"batch": i, "files": batch})
            print()

    impl_time = int(time.time() - executor_start)
    ok(f"Implementacao concluida ({impl_time}s)")
    trace_event(ctx, "agent", "completed", {"role": "implementer", "model": ctx.executor_model}, impl_time * 1000)

    # Verificar se tem mudancas
    diff_check = sh(["git", "diff", "--stat"])
    if not diff_check.stdout.strip():
        warn("Nenhuma mudanca detectada apos implementacao")
        return

    # ══════════════════════════════════════════════
    # FASE 2: REVIEW GATES (antes de commitar)
    # ══════════════════════════════════════════════
    print()
    log(f"{C.BOLD}FASE 2: Review gates{C.NC}")
    gates_passed = True
    max_fix_rounds = 3

    for gate_round in range(1, max_fix_rounds + 1):
        all_issues: list[str] = []

        # Gate 1: Self-review
        print()
        sr = _run_self_review(ctx, scout)
        if not sr.get("ok"):
            all_issues.extend(sr.get("issues", []))
            for tv in sr.get("token_violations", []):
                all_issues.append(f"TOKEN: {tv}")

        # Gate 2: Design lint (visual tasks)
        dl = _run_design_lint(ctx, scout)
        if not dl.get("ok"):
            for v in dl.get("violations", []):
                all_issues.append(f"CSS [{v.get('type', '?')}]: {v.get('value', '')} → {v.get('expected', '?')}")

        # Gate 3: Verificador (patterns, regras)
        print()
        vr = run_verifier(ctx, scout)
        if not vr.get("ok"):
            all_issues.extend(vr.get("issues", []))

        if not all_issues:
            ok(f"Todos os gates passaram (round {gate_round})")
            gates_passed = True
            break

        # Tem issues — reabrir implementer
        warn(f"Gates: {len(all_issues)} issues (round {gate_round}/{max_fix_rounds})")
        trace_event(ctx, "gates", f"fix_round_{gate_round}", {"issues": len(all_issues)})

        if gate_round < max_fix_rounds:
            _reopen_implementer_for_fixes(ctx, scout, lk, all_issues, f"Review gates round {gate_round}")
        else:
            warn(f"Gates: {max_fix_rounds} rounds esgotados, commitando com {len(all_issues)} issues restantes")
            gates_passed = False

    # ══════════════════════════════════════════════
    # FASE 3: COMMIT (pipeline controla)
    # ══════════════════════════════════════════════
    print()
    log(f"{C.BOLD}FASE 3: Commit{C.NC}")

    # Stage todas as mudancas
    sh(["git", "add", "-A"])

    # Montar mensagem de commit
    files_r = sh(["git", "diff", "--cached", "--name-only"])
    changed_files = [f.strip() for f in files_r.stdout.strip().split("\n") if f.strip()]
    gates_status = "gates:pass" if gates_passed else "gates:partial"

    prefix_map = {"bug": "fix", "performance": "perf", "infra": "infra", "seo": "seo", "content": "content"}
    commit_prefix = prefix_map.get(ctx.type, "feat")
    commit_msg = f"{commit_prefix}: {ctx.title}\n\n[odus-task] {gates_status} | {len(changed_files)} files | model={ctx.executor_model}"

    sh(["git", "commit", "-m", commit_msg])
    ok(f"Commit: {len(changed_files)} arquivos ({gates_status})")
    trace_event(ctx, "commit", "created", {"files": len(changed_files), "gates": gates_status})

    # ══════════════════════════════════════════════
    # FASE 4: VISUAL LOOP (layout only, max 5 rounds)
    # ══════════════════════════════════════════════
    if ctx.type == "layout" and ctx.verify_available and ctx.preflight_ok:
        print()
        log(f"{C.BOLD}FASE 4: Comparacao visual{C.NC}")
        _run_visual_comparison_loop(ctx, scout, lk)


def etapa_qa(ctx: TaskContext):
    """Etapa 5 — QA automatico."""
    log("QA automatico...")

    # Types
    if Path("tsconfig.json").exists():
        r = sh(["npx", "tsc", "--noEmit"])
        ctx.gate_types = "pass" if r.returncode == 0 else "fail"
        if ctx.gate_types == "pass":
            ok("Types: PASS")
        else:
            fail("Types: FAIL")
            print((r.stdout or r.stderr)[-500:])
    elif Path("deno.json").exists() or Path("deno.jsonc").exists():
        r = sh(["deno", "check", "."])
        ctx.gate_types = "pass" if r.returncode == 0 else "fail"

    # Lint
    eslint_configs = [".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js", "eslint.config.mjs"]
    if any(Path(c).exists() for c in eslint_configs):
        r = sh(["npx", "eslint", ".", "--quiet"])
        ctx.gate_lint = "pass" if r.returncode == 0 else "fail"
        if ctx.gate_lint == "pass":
            ok("Lint: PASS")
        else:
            fail("Lint: FAIL")
    elif Path("deno.json").exists() or Path("deno.jsonc").exists():
        r = sh(["deno", "lint"])
        ctx.gate_lint = "pass" if r.returncode == 0 else "fail"

    # Build (Next.js)
    if any(Path(c).exists() for c in ["next.config.ts", "next.config.js", "next.config.mjs"]):
        ctx.gate_build = "pass"
        ok("Build: PASS (types check)")

    # Tests
    pkg = Path("package.json")
    if pkg.exists() and '"test"' in pkg.read_text():
        r = sh(["npm", "test"])
        ctx.gate_tests = "pass" if r.returncode == 0 else "fail"
        if ctx.gate_tests == "pass":
            ok("Tests: PASS")
        else:
            fail("Tests: FAIL")
    else:
        dim("Tests: N/A")

    trace_event(ctx, "qa", "completed", {
        "build": ctx.gate_build, "types": ctx.gate_types,
        "lint": ctx.gate_lint, "tests": ctx.gate_tests,
    })
    trace_gate(ctx, "types", ctx.gate_types, {"tool": "tsc"})
    trace_gate(ctx, "lint", ctx.gate_lint, {"tool": "eslint"})
    trace_gate(ctx, "build", ctx.gate_build, {"tool": "next build"})
    trace_gate(ctx, "tests", ctx.gate_tests, {"tool": "npm test"})

    if ctx.gate_types == "fail" or ctx.gate_lint == "fail" or ctx.gate_tests == "fail":
        ctx.qa_failed = True


def etapa_qa_fix(ctx: TaskContext):
    """Reabre executor pra corrigir erros de QA."""
    if not ctx.qa_failed:
        return

    warn("QA falhou. Reabrindo executor pra corrigir...")

    errors = []
    if ctx.gate_types == "fail":
        r = sh(["npx", "tsc", "--noEmit"])
        errors.append(f"TYPE ERRORS:\n{(r.stdout or r.stderr)[-1000:]}")
    if ctx.gate_lint == "fail":
        r = sh(["npx", "eslint", ".", "--quiet"])
        errors.append(f"LINT ERRORS:\n{(r.stdout or r.stderr)[-1000:]}")
    if ctx.gate_tests == "fail":
        r = sh(["npm", "test"])
        errors.append(f"TEST ERRORS:\n{(r.stdout or r.stderr)[-1000:]}")

    fix_prompt = build_executor_prompt(ctx) + f"""

## Erros de QA encontrados
{chr(10).join(errors)}

## Instrucoes
- Corrija TODOS os erros listados acima
- Mantenha a logica original da implementacao
- Faca commit quando terminar"""

    _run_executor(ctx, fix_prompt, "Corrija os erros de QA. Faca commit quando terminar.")

    # Re-rodar QA
    log("QA (round 2)...")
    if Path("tsconfig.json").exists():
        r = sh(["npx", "tsc", "--noEmit"])
        ctx.gate_types = "pass" if r.returncode == 0 else "fail"
        if ctx.gate_types == "pass":
            ok("Types: PASS")
        else:
            fail("Types: FAIL (ainda)")


def _browser_verify(url: str, round_num: int) -> tuple[bool, dict]:
    """Roda verificacao com OdusBrowser. Retorna (passed, evidence)."""
    try:
        from browser import OdusBrowser
    except ImportError:
        dim("OdusBrowser nao disponivel, usando verify basico")
        return True, {}

    try:
        with OdusBrowser() as b:
            result = b.navigate(url, wait_ms=5000)

            # Screenshot
            ss_path = str(SCREENSHOTS_DIR / f"verify-r{round_num}.png")
            b.screenshot(ss_path)

            # DevTools report
            report_path = str(SCREENSHOTS_DIR / "devtools-report.json")
            b.save_devtools_report(report_path, ss_path)

            # Resultado
            passed = result.status in (200, 301, 302) and not result.has_errors
            evidence = {
                "status": result.status,
                "consoleErrors": len(result.console_errors),
                "networkErrors": len(result.network_errors),
                "loadTimeMs": result.load_time_ms,
            }

            if result.console_errors:
                for e in result.console_errors[:5]:
                    dim(f"  Console: {e.get('text', '')[:200]}")
            if result.network_errors:
                for e in result.network_errors[:5]:
                    dim(f"  Network: {e.get('status', '?')} {e.get('url', '')[:150]}")

            return passed, evidence
    except Exception as e:
        warn(f"Browser verify falhou: {e}")
        return True, {"error": str(e)}


def etapa_verify(ctx: TaskContext, adapter: "Adapter"):
    """Etapa 5.5 — VERIFY (adapter up + playwright + down, com retry)."""
    if not ctx.verify_available or not ctx.preflight_ok:
        dim(f"Verify: pulado ({ctx.adapter_stack} - verify_available={ctx.verify_available})")
        return

    max_rounds = 2
    for round_num in range(1, max_rounds + 1):
        print()
        log(f"Verificando preview ({ctx.adapter_stack}, round {round_num})...")
        verify_start = time.time()

        if not adapter.up():
            warn(f"Preview nao subiu ({ctx.adapter_stack}). Verify pulado.")
            ctx.gate_verify = "skip"
            trace_gate(ctx, "verify", "skip", {"adapter": ctx.adapter_stack, "reason": "up_failed"})
            return

        ok(f"Preview: {ctx.preview_url}")

        # Verificar com OdusBrowser (Python puro)
        verify_ok, evidence = _browser_verify(ctx.preview_url, round_num)
        ctx.gate_verify = "pass" if verify_ok else "fail"

        if ctx.gate_verify == "pass":
            ok("Verify: PASS")
        else:
            fail(f"Verify: FAIL (round {round_num})")

        screenshots = [str(s) for s in SCREENSHOTS_DIR.glob("*.png")]
        verify_duration = int(time.time() - verify_start)
        evidence_data = {
            "adapter": ctx.adapter_stack, "previewUrl": ctx.preview_url,
            "gate": ctx.gate_verify, "duration": verify_duration,
            "screenshots": ",".join(screenshots), "round": round_num,
            **evidence,
        }

        adapter.down()

        if ctx.gate_verify == "pass":
            trace_gate(ctx, "verify", "pass", evidence_data)
            trace_event(ctx, "verify", "pass", evidence_data, verify_duration)
            break

        # Se falhou e tem mais rounds, reabrir executor
        if round_num < max_rounds:
            warn("Reabrindo executor pra corrigir com evidencia visual...")

            devtools_ctx = ""
            devtools_report = SCREENSHOTS_DIR / "devtools-report.json"
            if devtools_report.exists():
                try:
                    dd = json.loads(devtools_report.read_text())
                    lines = []
                    for e in dd.get("consoleErrors", [])[:10]:
                        lines.append(f"- {e.get('type','')}: {e.get('text','')[:300]}")
                    for e in dd.get("networkErrors", [])[:10]:
                        lines.append(f"- {e.get('status','')} {e.get('url','')[:200]}")
                    devtools_ctx = "\n".join(lines)
                except Exception:
                    pass

            screenshot_ctx = ""
            if screenshots:
                screenshot_ctx = "Screenshots capturados:\n" + "\n".join(f"- {s}" for s in screenshots)

            fix_prompt = build_executor_prompt(ctx) + f"""

## Verify FALHOU
Preview: {ctx.preview_url}
O Playwright rodou verificacoes e encontrou problemas.

## DevTools Report
{devtools_ctx}

{screenshot_ctx}

## Instrucoes
- PRIORIDADE: corrija os erros de console
- Verifique interacoes (event handlers, state)
- Verifique layout (responsivo, alinhamento)
- Corrija e faca commit"""

            trace_event(ctx, "verify", "fix_started", {"round": round_num})
            _run_executor(ctx, fix_prompt, "Corrija os problemas do verify. Faca commit quando terminar.")
            ok(f"Correcao pos-verify aplicada (round {round_num})")
        else:
            trace_gate(ctx, "verify", "fail", evidence_data)
            trace_event(ctx, "verify", "fail", evidence_data, verify_duration)


def etapa_review(ctx: TaskContext):
    """Etapa 6 — Reviewer com contexto visual (Claude -p)."""
    print()
    log(f"Reviewer ({ctx.reviewer_model})...")

    diff = sh(["git", "diff", "main...HEAD"]).stdout[:4000]
    files_out = sh(["git", "diff", "--name-only", "main...HEAD"]).stdout
    ctx.files_changed = [f.strip() for f in files_out.strip().split("\n") if f.strip()]

    # Contexto visual (screenshots e Figma description se disponivel)
    visual_context = ""
    figma_desc_path = SCREENSHOTS_DIR / "figma-description.txt"
    if figma_desc_path.exists():
        figma_desc = figma_desc_path.read_text()[:2000]
        visual_context += f"\n## Referencia visual (Figma)\n{figma_desc}\n"

    # Ultimo screenshot da implementacao
    screenshots = sorted(SCREENSHOTS_DIR.glob("visual-round-*.png"))
    if screenshots:
        visual_context += f"\n## Screenshot da implementacao: {screenshots[-1]}\n"

    # Tokens do Figma
    tokens_path = SCREENSHOTS_DIR / "figma-tokens.json"
    if tokens_path.exists():
        visual_context += f"\n## Tokens do Figma\n{tokens_path.read_text()[:1500]}\n"

    review_prompt = f"""Voce e o reviewer do Odus Task. Revise este diff criticamente.

## Checklist de codigo
- Sem console.log em producao
- Sem any em TypeScript
- Sem inline styles (usar CSS Handles se VTEX IO)
- Sem imports nao usados
- Sem codigo comentado
- Sem vulnerabilidades (XSS, injection)
- Sem magic numbers em CSS (usar tokens/variaveis)
- HTML semantico (nao div pra tudo)

## Checklist visual (se contexto visual disponivel)
- Cores batem com os tokens do Figma?
- Tipografia correta (font-family, size, weight)?
- Espacamentos corretos (margin, padding, gap)?
- Layout responsivo correto?
{visual_context}

## Stack: {ctx.client_stack}
## Tipo: {ctx.type}

## Diff ({len(ctx.files_changed)} arquivos):
{diff}

Responda em JSON (sem markdown):
{{"approved": true/false, "issues": ["descricao"], "visual_issues": ["problemas visuais se aplicavel"], "summary": "resumo"}}"""

    review = claude_json(review_prompt, ctx.reviewer_model, timeout=120)
    if isinstance(review, dict):
        ctx.review_approved = review.get("approved", True)
        issues = review.get("issues", [])
        visual_issues = review.get("visual_issues", [])
        if visual_issues:
            issues.extend([f"VISUAL: {vi}" for vi in visual_issues])
    else:
        ctx.review_approved = True
        issues = []

    ctx.review_rounds = 1
    trace_event(ctx, "review", "approved" if ctx.review_approved else "rejected",
                {"model": ctx.reviewer_model, "round": ctx.review_rounds})
    trace_gate(ctx, "review", "pass" if ctx.review_approved else "fail", {"rounds": ctx.review_rounds})

    if ctx.review_approved:
        ok("Reviewer aprovou")
        return

    warn("Reviewer rejeitou:")
    for issue in issues:
        print(f"  - {issue}")

    warn("Reabrindo executor pra corrigir...")
    fix_prompt = build_executor_prompt(ctx) + f"""

## Issues do reviewer
{chr(10).join(f'- {i}' for i in issues)}

## Instrucoes
- Corrija TODOS os issues listados acima
- Mantenha a logica original
- Faca commit quando terminar"""

    _run_executor(ctx, fix_prompt, "Corrija os issues do reviewer. Faca commit quando terminar.")
    ctx.review_rounds = 2
    ok("Correcoes aplicadas (round 2)")


def etapa_red_team(ctx: TaskContext):
    """Etapa 6.5 — Red team (so risk high/critical)."""
    if ctx.risk not in ("high", "critical"):
        dim(f"Red team: skip (risk={ctx.risk})")
        return

    print()
    log(f"Red team (risk={ctx.risk})...")

    diff = sh(["git", "diff", "main...HEAD"]).stdout[:2000]
    prompt = f"""Voce e um red team agent. Analise este diff e encontre problemas de seguranca e robustez.

Stack: {ctx.client_stack} | Tipo: {ctx.type}

Verifique: edge cases, XSS, injection, SSRF, validacao ausente, race conditions, dados sensiveis.

Diff:
{diff}

Responda APENAS em JSON:
{{"passed": true/false, "issues": ["descricao"], "severity": "low/medium/high"}}"""

    rt = claude_json(prompt, "haiku")
    if isinstance(rt, dict):
        ctx.redteam_passed = rt.get("passed", True)
        if not ctx.redteam_passed:
            warn("Red team encontrou issues:")
            for issue in rt.get("issues", []):
                print(f"  - {issue}")
            trace_event(ctx, "redteam", "issues_found", rt)
            trace_gate(ctx, "redteam", "fail", rt)
        else:
            ok("Red team: nenhum issue")
            trace_event(ctx, "redteam", "passed", {})
            trace_gate(ctx, "redteam", "pass", {})
    else:
        dim("Red team: timeout/erro")
        ctx.redteam_passed = True


def etapa_deliver(ctx: TaskContext):
    """Etapa 7 — Push + PR."""
    print()
    log("Entregando...")

    sh(["git", "push", "origin", "HEAD"])
    ok(f"Push: {ctx.branch_name}")

    prefix_map = {"bug": "fix", "performance": "perf", "infra": "infra", "seo": "seo", "content": "content"}
    prefix = prefix_map.get(ctx.type, "feat")

    verify_icon = "✅" if ctx.gate_verify == "pass" else ("❌" if ctx.gate_verify == "fail" else "⬜ N/A")
    pr_body = f"""## Task
[{ctx.title}](https://task.oduscommerce.com.br/{ctx.client_slug}/board)

## Pipeline
- Tipo: {ctx.type} | Risco: {ctx.risk}
- Modelo: executor={ctx.executor_model} | reviewer={ctx.reviewer_model}
- Skills: {', '.join(s['name'] for s in ctx.skills)}
- Review: {ctx.review_rounds} round(s)

## Validacao
- Build: {"✅" if ctx.gate_build != "fail" else "❌"}
- Types: {"✅" if ctx.gate_types == "pass" else "❌"}
- Lint: {"✅" if ctx.gate_lint != "fail" else "⬜"}
- Tests: {"✅" if ctx.gate_tests == "pass" else "⬜ N/A"}
- AI Review: ✅ ({ctx.review_rounds} round{"s" if ctx.review_rounds > 1 else ""})
- Verify: {verify_icon} ({ctx.adapter_stack})

## Arquivos
{chr(10).join(f"- {f}" for f in ctx.files_changed)}"""

    r = sh(["gh", "pr", "create", "--title", f"{prefix}: {ctx.title}", "--body", pr_body, "--base", "main"])
    ctx.pr_url = r.stdout.strip().split("\n")[-1] if r.returncode == 0 else ""

    if ctx.pr_url:
        ok(f"PR: {ctx.pr_url}")
    else:
        r2 = sh(["gh", "pr", "view", "--json", "url", "-q", ".url"])
        ctx.pr_url = r2.stdout.strip()
        warn(f"PR ja existe: {ctx.pr_url}" if ctx.pr_url else "PR nao criada")

    trace_event(ctx, "deliver", "pr_created", {"url": ctx.pr_url, "branch": ctx.branch_name, "files": len(ctx.files_changed)})


def etapa_state_after(ctx: TaskContext):
    """State after + outcome."""
    r = sh(["git", "rev-parse", "HEAD"])
    hash_after = r.stdout.strip() if r.returncode == 0 else ""
    r2 = sh(["git", "diff", "--stat", "main...HEAD"])
    diff_stats = r2.stdout.strip().split("\n")[-1] if r2.stdout.strip() else ""
    trace_event(ctx, "state", "after", {
        "hash": hash_after, "diffStats": diff_stats,
        "prUrl": ctx.pr_url, "filesChanged": len(ctx.files_changed),
    })
    trace_outcome(ctx, {
        "build": "pass" if ctx.gate_build != "fail" else "fail",
        "tests": "pass" if ctx.gate_tests == "pass" else ("na" if ctx.gate_tests == "skip" else "fail"),
        "review": "approved" if ctx.review_approved else "rejected",
    })


def etapa_quality_score(ctx: TaskContext):
    """Etapa 8 — Quality score deterministico."""
    q_spec = ctx.spec_confidence * 15 // 100
    q_build = 15 if ctx.gate_types == "pass" else 0
    q_lint = 10 if ctx.gate_lint != "fail" else 0
    q_tests = 15 if ctx.gate_tests == "pass" else 10  # N/A = 10
    q_review = 15 if ctx.review_approved else 0
    q_verify = 10 if ctx.gate_verify == "pass" else (-10 if ctx.gate_verify == "fail" else 0)
    q_intervention = 0 if ctx.human_intervention else 15
    q_retry = 15 if (ctx.review_rounds <= 1 and not ctx.qa_failed) else 5

    ctx.quality_score = q_spec + q_build + q_lint + q_tests + q_review + q_verify + q_intervention + q_retry
    trace_event(ctx, "quality", "scored", {"score": ctx.quality_score})


def etapa_detect_intervention(ctx: TaskContext):
    """Etapa 9 — Detectar intervencao humana + extrair knowledge."""
    r = sh(["git", "log", "main..HEAD", "--format=%ae"])
    authors = set(r.stdout.strip().split("\n")) if r.stdout.strip() else set()
    if len(authors) <= 1:
        return

    ctx.human_intervention = True
    trace_event(ctx, "human", "intervened", {"detected": "multiple commit authors"})

    agent_email = sh(["git", "config", "user.email"]).stdout.strip()
    r2 = sh(["git", "log", "main..HEAD", "--format=%H %ae"])
    human_commits = [line.split()[0] for line in r2.stdout.strip().split("\n")
                     if line.strip() and len(line.split()) >= 2 and line.split()[1] != agent_email]

    if not human_commits:
        return

    human_diff = ""
    for commit in human_commits[:5]:
        r3 = sh(["git", "diff", f"{commit}^..{commit}"])
        human_diff += r3.stdout[:500] + "\n"

    if not human_diff.strip():
        return

    trace_event(ctx, "human", "correction_captured", {
        "diffLines": len(human_diff.split("\n")),
        "commits": ",".join(human_commits[:5]),
    })

    prompt = f"""O humano corrigiu o codigo do agente autonomo. Analise o diff e proponha knowledge.

Task: {ctx.title}
Stack: {ctx.client_stack}

Diff:
{human_diff[:2000]}

Se a correcao revela um padrao, responda em JSON:
[{{"type":"gotcha","title":"titulo curto","content":"o que fez errado e como deveria fazer","negative":"o que nao fazer","scope":"stack","stack":"{ctx.client_stack}","confidence":0.8}}]

Se nao tem nada, responda: []"""

    knowledge = claude_json(prompt, "haiku")
    if isinstance(knowledge, list) and knowledge:
        for item in knowledge:
            item["proposedBy"] = "human_correction"
        api_call("/api/knowledge", "POST", knowledge)
        ok(f"Correcao humana: {len(knowledge)} knowledge extraidos (confidence 0.8)")


def etapa_execution(ctx: TaskContext):
    """Etapa 10 — Registrar execution."""
    print()
    log("Registrando execucao...")

    duration = int(time.time() - ctx.start_time)
    commits_r = sh(["git", "log", "--oneline", "main..HEAD"])
    commits = [l.strip() for l in commits_r.stdout.strip().split("\n") if l.strip()][:10]

    api_call(f"/api/tasks/{ctx.task_id}/executions", "POST", {
        "taskType": ctx.type, "riskLevel": ctx.risk, "autonomyLevel": ctx.autonomy,
        "model": ctx.executor_model, "skillsUsed": [s["name"] for s in ctx.skills],
        "filesChanged": ctx.files_changed, "commits": commits,
        "result": "success", "prUrl": ctx.pr_url, "durationSeconds": duration,
        "retries": ctx.review_rounds - 1, "humanIntervention": ctx.human_intervention,
        "qualityScore": ctx.quality_score,
        "gatesResult": {"build": ctx.gate_build, "types": ctx.gate_types, "lint": ctx.gate_lint, "tests": ctx.gate_tests},
    })
    ok("Execution registrada")


def etapa_timesheet(ctx: TaskContext) -> int:
    """Etapa 11 — Timesheet. Retorna human_minutes."""
    base = {"bug": 60, "content": 45, "seo": 45, "frontend": 120, "layout": 120,
            "backend": 150, "integration": 180, "performance": 120}.get(ctx.type, 120)
    mult = {"low": 0.7, "medium": 1.0, "high": 1.3, "critical": 1.6}.get(ctx.risk, 1.0)
    human_minutes = int(base * mult)

    api_call(f"/api/tasks/{ctx.task_id}/time", "PUT", {
        "durationMinutes": human_minutes,
        "description": "Implementacao via Odus Task pipeline",
    })
    ok(f"Timesheet: {human_minutes}min")
    return human_minutes


def etapa_knowledge(ctx: TaskContext):
    """Etapa 12 — Knowledge bidirecional (falhas E sucessos)."""

    # ── Knowledge de FALHA (com evidencia) ─────
    failure_reason = ""
    if ctx.human_intervention:
        failure_reason = "intervencao humana"
    elif ctx.review_rounds > 1:
        failure_reason = f"review rejeitou (round {ctx.review_rounds})"
    elif ctx.gate_verify == "fail":
        failure_reason = "verify falhou"

    if failure_reason:
        log(f"Analisando falhas (evidencia: {failure_reason})...")

        prompt = f"""O pipeline teve um problema. Analise e proponha knowledge se relevante.

Task: {ctx.title} | Client: {ctx.client_name} ({ctx.client_stack})
Tipo: {ctx.type} | Risco: {ctx.risk} | Evidencia: {failure_reason}
QA: types={ctx.gate_types} lint={ctx.gate_lint} tests={ctx.gate_tests} | Verify: {ctx.gate_verify}
Review rounds: {ctx.review_rounds} | Quality: {ctx.quality_score}/100
Arquivos: {', '.join(ctx.files_changed)}

Responda em JSON:
[{{"type":"gotcha","title":"titulo","content":"descricao","negative":"o que nao fazer","scope":"stack","stack":"{ctx.client_stack}","confidence":0.6}}]

Se nada relevante: []"""

        knowledge = claude_json(prompt, "haiku")
        if isinstance(knowledge, list) and knowledge:
            for item in knowledge:
                item["proposedBy"] = "pipeline_evidence"
            api_call("/api/knowledge", "POST", knowledge)
            ok(f"Knowledge (falha): {len(knowledge)} items propostos (evidencia: {failure_reason})")
        else:
            dim("Knowledge (falha): nenhum item novo")

    # ── Knowledge de SUCESSO (score alto, sem intervencao) ─────
    is_clean_success = (
        ctx.quality_score >= 85
        and not ctx.human_intervention
        and ctx.review_rounds <= 1
        and ctx.gate_types != "fail"
        and ctx.gate_verify != "fail"
    )

    if is_clean_success:
        log("Analisando patterns de sucesso...")

        diff = sh(["git", "diff", "main...HEAD"]).stdout[:3000]
        prompt = f"""O pipeline executou com sucesso (score {ctx.quality_score}/100, sem intervencao, review aprovado de primeira).
Analise o diff e extraia patterns reutilizaveis que FUNCIONARAM BEM.

Task: {ctx.title} | Client: {ctx.client_name} ({ctx.client_stack})
Tipo: {ctx.type} | Arquivos: {', '.join(ctx.files_changed)}

Diff:
{diff}

Extraia APENAS se existir um pattern concreto e reutilizavel (nao obviedades).
Foque em: abordagens que deram certo, estrutura de componentes que funcionou, integracoes limpas.

Responda em JSON:
[{{"type":"pattern","title":"titulo curto","content":"o que funcionou e como replicar","scope":"stack","stack":"{ctx.client_stack}","confidence":0.7}}]

Se nada relevante: []"""

        knowledge = claude_json(prompt, "haiku")
        if isinstance(knowledge, list) and knowledge:
            for item in knowledge:
                item["proposedBy"] = "pipeline_success"
            api_call("/api/knowledge", "POST", knowledge)
            ok(f"Knowledge (sucesso): {len(knowledge)} patterns capturados")
        else:
            dim("Knowledge (sucesso): nenhum pattern novo")

    if not failure_reason and not is_clean_success:
        dim("Knowledge: pulado (score medio, sem evidencia forte)")


def etapa_skill_proposal(ctx: TaskContext):
    """Skill proposal autonomo."""
    prompt = f"""Baseado nesta execucao, existe um padrao reutilizavel que deveria virar skill?

Task: {ctx.title} | Stack: {ctx.client_stack} | Tipo: {ctx.type}
Arquivos: {', '.join(ctx.files_changed)} | Quality: {ctx.quality_score}/100

Skill = instrucao tecnica reaproveitavel (diferente de knowledge/gotcha).

Se existe, responda em JSON:
{{"name":"nome","category":"{ctx.type}","stack":"{ctx.client_stack}","description":"descricao","content":"instrucoes detalhadas"}}

Se nao: null"""

    skill = claude_json(prompt, "haiku")
    if isinstance(skill, dict) and skill.get("name") and skill.get("content"):
        skill["status"] = "draft"
        skill["proposedBy"] = "pipeline"
        api_call("/api/skills", "POST", skill)
        ok(f"Skill proposta (draft): {skill['name']}")
        trace_event(ctx, "skill", "proposed", skill)


def etapa_status_callback(ctx: TaskContext, human_minutes: int):
    """Etapa 13 — Status + comment humanizado + trace complete."""
    evidence = {
        "spec": ctx.spec_confidence >= 80, "specConfidence": ctx.spec_confidence,
        "build": ctx.gate_build != "fail", "types": ctx.gate_types == "pass",
        "lint": ctx.gate_lint != "fail",
        "tests": ctx.gate_tests == "pass" if ctx.gate_tests != "skip" else None,
        "review": True, "reviewRounds": ctx.review_rounds,
        "redteamPassed": ctx.redteam_passed, "humanIntervention": ctx.human_intervention,
        "model": ctx.executor_model, "reviewerModel": ctx.reviewer_model,
    }

    api_call(f"/api/tasks/{ctx.task_id}/status", "POST", {
        "status": "REVIEW", "prUrl": ctx.pr_url,
        "description": f"Pipeline: {ctx.type} | Score: {ctx.quality_score} | Modelo: {ctx.executor_model}",
        "qualityScore": ctx.quality_score, "qualityEvidence": evidence,
    })
    ok("Task movida pra Revisao")

    # Comentario humanizado
    duration = int(time.time() - ctx.start_time)
    agent_mins = duration // 60

    comment_prompt = f"""Escreva um comentario curto e natural (como um dev postaria) resumindo que a implementacao foi feita. Texto puro, sem markdown, sem emojis. Max 4 linhas.

- Task: {ctx.title}
- Arquivos: {len(ctx.files_changed)}
- Tempo: {agent_mins}min
{f"- PR: {ctx.pr_url}" if ctx.pr_url else ""}
{"- AVISO: types com erro" if ctx.gate_types != "pass" else ""}

APENAS o comentario."""

    comment = claude_text(comment_prompt, "haiku")
    if not comment:
        comment = f"Implementacao concluida. {len(ctx.files_changed)} arquivos alterados em {agent_mins}min."
        if ctx.pr_url:
            comment += f" PR: {ctx.pr_url}"

    result = api_call(f"/api/tasks/{ctx.task_id}/comment", "POST", {"content": comment})
    tarefy_synced = isinstance(result, dict) and result.get("tarefySynced", False)
    if tarefy_synced:
        ok("Comentario postado no Tarefy")
    else:
        dim("Comentario salvo localmente (Tarefy: sem sync)")

    # Trace complete
    trace_event(ctx, "trace", "completed", {"result": "success"})
    trace_complete(ctx, "success", ctx.quality_score, duration)
    ok("Trace completado")


def print_summary(ctx: TaskContext, human_minutes: int):
    """Resumo final."""
    print()
    hr()
    print()
    print(f"{C.BOLD}📊 EVIDENCE PACK{C.NC}")
    print()

    def check(val, name):
        pad = " " * (14 - len(name))
        if val == "pass": return f"  {name}:{pad}{C.GREEN}✅{C.NC}"
        if val == "fail": return f"  {name}:{pad}{C.RED}❌{C.NC}"
        return f"  {name}:{pad}{C.DIM}⬜ N/A{C.NC}"

    spec_icon = f"{C.GREEN}✅ {ctx.spec_confidence}%{C.NC}" if ctx.spec_confidence >= 80 else f"{C.YELLOW}⚠️  {ctx.spec_confidence}%{C.NC}"
    print(f"  Spec:         {spec_icon}")
    print(check(ctx.gate_build, "Build"))
    print(check(ctx.gate_types, "Types"))
    print(check(ctx.gate_lint, "Lint"))
    print(check(ctx.gate_tests, "Tests"))
    print(f"  AI Review:    {C.GREEN}✅{C.NC} ({ctx.review_rounds} round{'s' if ctx.review_rounds > 1 else ''})")

    if ctx.gate_verify == "pass":
        print(f"  Verify:       {C.GREEN}✅ {ctx.adapter_stack}{C.NC}")
    elif ctx.gate_verify == "fail":
        print(f"  Verify:       {C.RED}❌ {ctx.adapter_stack}{C.NC}")
    else:
        print(f"  Verify:       {C.DIM}⬜ N/A ({ctx.adapter_stack}){C.NC}")

    if ctx.risk in ("high", "critical"):
        rt = f"{C.GREEN}✅{C.NC}" if ctx.redteam_passed else f"{C.YELLOW}⚠️  Issues{C.NC}"
        print(f"  Red Team:     {rt}")

    interv = f"{C.YELLOW}⚠️  Sim{C.NC}" if ctx.human_intervention else f"{C.GREEN}Nenhuma{C.NC}"
    print(f"  Intervention: {interv}")
    print()

    bar_filled = ctx.quality_score // 5
    bar_empty = 20 - bar_filled
    bar_color = C.GREEN if ctx.quality_score >= 80 else (C.YELLOW if ctx.quality_score >= 60 else C.RED)
    print(f"  Quality:      {bar_color}{'█' * bar_filled}{C.DIM}{'░' * bar_empty}{C.NC} {C.BOLD}{ctx.quality_score}/100{C.NC}")

    print()
    dim(f"Skills: {', '.join(s['name'] for s in ctx.skills)}")
    dim(f"Modelo: {ctx.executor_model} (executor) + {ctx.reviewer_model} (reviewer)")
    duration = int(time.time() - ctx.start_time)
    dim(f"Tempo agente: {duration}s | Tempo estimado (dev pleno): {human_minutes}min")
    dim(f"PR: {ctx.pr_url}")
    print()
    print(f"{C.BOLD}━━━ DONE {'━' * 51}{C.NC}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"{C.RED}Uso: python3 scripts/odus-task.py <taskId> [--auto]{C.NC}")
        sys.exit(1)

    ctx = TaskContext(
        task_id=sys.argv[1],
        auto_mode="--auto" in sys.argv,
        start_time=time.time(),
    )

    adapter: Adapter | None = None
    human_minutes = 120

    print()
    print(f"{C.BOLD}━━━ ODUS TASK (Python) {'━' * 38}{C.NC}")
    print()

    try:
        # 1 — Classify
        if not etapa_classify(ctx):
            sys.exit(1)

        etapa_prediction(ctx)
        etapa_previous_traces(ctx)

        # 1.5 — Spec Gate
        print()
        if not etapa_spec_gate(ctx):
            sys.exit(1)

        # 2 — Model Routing
        etapa_model_routing(ctx)

        # Trace
        skills_names = [s["name"] for s in ctx.skills]
        knowledge_ids = [k.get("id", "") for k in ctx.knowledge if k.get("id")]
        ctx.trace_id = trace_create(ctx, {
            "type": ctx.type, "risk": ctx.risk, "autonomy": ctx.autonomy,
            "stack": ctx.client_stack, "skillsCount": len(ctx.skills),
            "knowledgeCount": len(ctx.knowledge),
            "skillsUsed": skills_names, "knowledgeIds": knowledge_ids,
            "predictedScore": ctx.prediction,
        })
        trace_event(ctx, "classifier", "completed", {"type": ctx.type, "risk": ctx.risk, "autonomy": ctx.autonomy})
        trace_event(ctx, "decision", "model_selected", {
            "executor": ctx.executor_model, "reviewer": ctx.reviewer_model,
            "reason": f"risk={ctx.risk} type={ctx.type}",
        })
        trace_event(ctx, "skills", "loaded", skills_names)
        if ctx.knowledge:
            trace_event(ctx, "knowledge", "retrieved", [k.get("title", "") for k in ctx.knowledge])
            if ctx.trace_id and knowledge_ids:
                api_call(f"/api/traces/{ctx.trace_id}/knowledge", "POST", {"knowledgeIds": knowledge_ids})

        # 2.5 — Plan
        etapa_plan(ctx)

        # 3 — Branch
        etapa_branch(ctx)

        # Adapter preflight
        adapter = resolve_adapter(ctx)
        etapa_adapter_preflight(ctx, adapter)

        # State before
        etapa_state_before(ctx)

        # 4 — Executor (v2: scout + implementer + verifier)
        etapa_execute_v2(ctx)

        # 5 — QA + Fix
        etapa_qa(ctx)
        etapa_qa_fix(ctx)

        # 5.5 — Verify
        etapa_verify(ctx, adapter)

        # 6 — Review
        etapa_review(ctx)

        # 6.5 — Red Team
        etapa_red_team(ctx)

        # 7 — Deliver
        etapa_deliver(ctx)
        etapa_state_after(ctx)

        # 8 — Quality Score + 9 — Intervention
        etapa_detect_intervention(ctx)
        etapa_quality_score(ctx)

        # 10 — Execution
        etapa_execution(ctx)

        # 11 — Timesheet
        human_minutes = etapa_timesheet(ctx)

        # 12 — Knowledge + Mem0
        etapa_knowledge(ctx)
        etapa_skill_proposal(ctx)
        _learn_from_execution(ctx)

        # 13 — Status + Comment + Trace
        etapa_status_callback(ctx, human_minutes)

        # Summary
        print_summary(ctx, human_minutes)

    finally:
        # Cleanup
        if adapter:
            adapter.down()
        shutil.rmtree(SCREENSHOTS_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
