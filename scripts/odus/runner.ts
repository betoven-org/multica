/**
 * Odus Task — Pi Runner (com fallback Claude Code)
 *
 * Tenta rodar Pi com extensoes Odus. Se Pi nao tem API key,
 * faz fallback pro Claude Code CLI (que usa Claude Max/Pro).
 *
 * Uso:
 *   ODUS_CONTEXT_FILE=/tmp/ctx.json \
 *   ODUS_TRACE_ID=abc123 \
 *   ODUS_BRANCH_NAME=feat/xxx \
 *   npx tsx runner.ts --model opus --message "Implemente a task" [--auto]
 */
import { parseArgs } from "node:util";
import { resolve } from "node:path";
import { execSync, spawnSync } from "node:child_process";
import { existsSync, writeFileSync, unlinkSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const { values } = parseArgs({
  options: {
    model: { type: "string", default: "sonnet" },
    message: { type: "string", default: "" },
    auto: { type: "boolean", default: false },
    "context-file": { type: "string", default: "" },
  },
});

// ── Runtime detection ────────────────────────────────────────────────────────

function hasPiAuth(): boolean {
  if (process.env.ANTHROPIC_API_KEY) return true;
  // Check pi auth.json
  const authFile = join(
    process.env.HOME || "~",
    ".pi",
    "agent",
    "auth.json"
  );
  if (existsSync(authFile)) {
    try {
      const auth = JSON.parse(readFileSync(authFile, "utf-8"));
      return Object.keys(auth).length > 0;
    } catch {}
  }
  return false;
}

// ── Model mapping ────────────────────────────────────────────────────────────

const PI_MODEL_MAP: Record<string, string> = {
  haiku: "claude-haiku-4-5",
  sonnet: "claude-sonnet-4-5",
  opus: "claude-opus-4-5",
};

// ── Pi runner ────────────────────────────────────────────────────────────────

function runPi(): void {
  const modelId =
    PI_MODEL_MAP[values.model || "sonnet"] ||
    values.model ||
    "claude-sonnet-4-5";

  const extDir = resolve(import.meta.dirname || ".", "extensions");
  const extensions = [
    resolve(extDir, "odus-context.ts"),
    resolve(extDir, "odus-trace.ts"),
    resolve(extDir, "odus-commit.ts"),
  ];

  const cmd: string[] = ["pi"];
  cmd.push("--provider", "anthropic");
  cmd.push("--model", modelId);
  cmd.push("--thinking", "medium");

  for (const ext of extensions) {
    cmd.push("-e", ext);
  }

  if (values.auto) {
    cmd.push("-p");
  }

  if (values.message) {
    cmd.push(values.message);
  }

  console.log(`\n[odus] Runtime: Pi`);
  console.log(`[odus] Modelo: ${modelId}`);
  console.log(`[odus] Extensoes: ${extensions.length}`);
  console.log(`[odus] Modo: ${values.auto ? "autonomo" : "interativo"}\n`);

  const result = spawnSync(cmd[0], cmd.slice(1), {
    stdio: "inherit",
    env: process.env,
    cwd: process.cwd(),
  });
  if (result.status && result.status !== 0) {
    throw Object.assign(new Error("Pi failed"), { status: result.status });
  }
}

// ── Claude Code fallback ─────────────────────────────────────────────────────

function runClaudeCode(): void {
  const model = values.model || "sonnet";
  const contextFile = values["context-file"] || process.env.ODUS_CONTEXT_FILE;

  const cmd: string[] = ["claude", "--model", model];

  // System prompt from context file
  if (contextFile && existsSync(contextFile)) {
    // Claude Code espera --append-system-prompt-file com texto, nao JSON
    // Converter o JSON pra texto de prompt
    const promptFile = join(tmpdir(), `odus-prompt-${process.pid}.txt`);
    try {
      const ctx = JSON.parse(readFileSync(contextFile, "utf-8"));
      const prompt = buildPromptFromContext(ctx);
      writeFileSync(promptFile, prompt);
      cmd.push("--append-system-prompt-file", promptFile);
    } catch {
      cmd.push("--append-system-prompt-file", contextFile);
    }
  }

  // Skip perms se auto
  if (values.auto) {
    cmd.splice(1, 0, "--dangerously-skip-permissions");
  }

  // Mensagem SEMPRE por ultimo (Claude Code pega ultimo arg como prompt)
  if (values.message) {
    cmd.push(values.message);
  }

  console.log(`\n[odus] Runtime: Claude Code (fallback)`);
  console.log(`[odus] Modelo: ${model}`);
  console.log(`[odus] Modo: ${values.auto ? "autonomo" : "interativo"}\n`);

  try {
    spawnSync(cmd[0], cmd.slice(1), {
      stdio: "inherit",
      env: process.env,
      cwd: process.cwd(),
    });
  } finally {
    // Cleanup temp files
    const promptFile = join(tmpdir(), `odus-prompt-${process.pid}.txt`);
    const mcpFile = join(tmpdir(), `odus-mcp-${process.pid}.json`);
    try { unlinkSync(promptFile); } catch {}
    try { unlinkSync(mcpFile); } catch {}
  }
}

// ── Prompt builder (reutiliza logica do odus-context.ts pra Claude Code) ────

function buildPromptFromContext(ctx: Record<string, unknown>): string {
  const lines: string[] = [
    `# Task: ${ctx.title || "?"}`,
    `Client: ${ctx.clientName || "?"} (${ctx.clientStack || "?"})`,
    "",
  ];

  if (ctx.description) {
    const clean = String(ctx.description)
      .replace(/<[^>]+>/g, " ")
      .trim()
      .slice(0, 3000);
    lines.push("## Descricao", clean, "");
  }

  const comments = ctx.comments as Array<Record<string, string>> | undefined;
  if (comments?.length) {
    lines.push(`## Comentarios (${comments.length})`);
    for (const c of comments) {
      lines.push(
        `**${c.author || "?"}** (${(c.date || "").slice(0, 10)}): ${c.content || ""}`
      );
    }
    lines.push("");
  }

  if (ctx.figmaUrl) {
    lines.push(
      "## Figma",
      `URL: ${ctx.figmaUrl}`,
      `FileKey: ${ctx.figmaFileKey || "?"} | NodeId: ${ctx.figmaNodeId || "?"}`,
      "Use o MCP Figma (get_design_context e get_screenshot) pra inspecionar.",
      ""
    );
  }

  if (ctx.stepsToReproduce) {
    lines.push("## Steps to reproduce", String(ctx.stepsToReproduce), "");
  }

  const sc = ctx.stackContext as Record<string, unknown> | undefined;
  if (sc?.rules) {
    lines.push("## Rules da stack", String(sc.rules), "");
  }
  if (Array.isArray(sc?.checklist) && sc.checklist.length) {
    lines.push("## Checklist");
    for (const item of sc.checklist as string[]) {
      lines.push(`- [ ] ${item}`);
    }
    lines.push("");
  }

  const skills = ctx.skills as Array<Record<string, string>> | undefined;
  if (skills?.length) {
    lines.push(`## Skills (${skills.length})`);
    for (const s of skills) {
      lines.push(`### ${s.name} (${s.category})`, (s.content || "").slice(0, 3000), "");
    }
  }

  const knowledge = ctx.knowledge as Array<Record<string, unknown>> | undefined;
  if (knowledge?.length) {
    lines.push(`## Knowledge (${knowledge.length})`);
    for (const k of knowledge) {
      lines.push(
        `### [${k.type}] ${k.title} (confidence: ${k.confidence})`,
        String(k.content)
      );
      if (k.negative) lines.push(`NAO FAZER: ${k.negative}`);
      lines.push("");
    }
  }

  const plan = ctx.plan as Record<string, unknown> | undefined;
  if (Array.isArray(plan?.steps) && plan.steps.length) {
    lines.push("## Plan");
    (plan.steps as string[]).forEach((s, i) => lines.push(`${i + 1}. ${s}`));
    if (Array.isArray(plan.files) && plan.files.length) {
      lines.push(`\nArquivos provaveis: ${(plan.files as string[]).join(", ")}`);
    }
    lines.push("");
  }

  if (ctx.memoryContext) {
    lines.push(String(ctx.memoryContext), "");
  }

  if (ctx.previousTraces) {
    lines.push(String(ctx.previousTraces), "");
  }

  lines.push(
    "## Instrucoes",
    "- Siga TODAS as rules e o checklist da stack",
    "- ZERO console.log em producao",
    `- Trabalhe APENAS na branch atual (${ctx.branchName || "?"})`,
    "- Quando terminar, faca commit e avise que terminou",
    "- NAO faca push e NAO crie PR (o orquestrador faz depois)",
    "",
    "## Regras de codigo (OBRIGATORIO)",
    "- SEMPRE escreva JSX/TSX moderno — NUNCA use React.createElement()",
    "- Use const/let — NUNCA use var",
    "- Use arrow functions, destructuring, optional chaining (?.), nullish coalescing (??)",
    "- Leia e edite APENAS arquivos fonte — NUNCA edite build/, dist/",
    "- Se encontrar codigo legado, modernize ao editar"
  );

  return lines.join("\n");
}

// ── Main ─────────────────────────────────────────────────────────────────────

if (hasPiAuth()) {
  try {
    runPi();
  } catch (err: unknown) {
    const code = (err as { status?: number }).status;
    if (code === 130) process.exit(0); // ctrl+c
    console.error("[odus] Pi falhou, tentando Claude Code...");
    runClaudeCode();
  }
} else {
  console.log("[odus] Pi sem auth — usando Claude Code");
  runClaudeCode();
}
