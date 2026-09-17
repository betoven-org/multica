/**
 * Extensao odus-context
 *
 * Injeta o contexto completo da task (classify, skills, knowledge, plan)
 * no system prompt ANTES do primeiro turno do executor.
 *
 * Recebe o contexto via env var ODUS_CONTEXT_FILE (path pra JSON).
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "fs";

interface TaskContext {
  title: string;
  clientName: string;
  clientStack: string;
  description: string;
  stepsToReproduce?: string;
  figmaUrl?: string;
  figmaFileKey?: string;
  figmaNodeId?: string;
  comments?: Array<{ author: string; date: string; content: string }>;
  skills?: Array<{ name: string; category: string; content: string }>;
  knowledge?: Array<{
    type: string;
    title: string;
    content: string;
    negative?: string;
    confidence: number;
  }>;
  stackContext?: { rules?: string; checklist?: string[] };
  plan?: { files?: string[]; steps?: string[]; risks?: string[] };
  previousTraces?: string;
  memoryContext?: string;
  branchName: string;
  type: string;
  risk: string;
}

function buildPrompt(ctx: TaskContext): string {
  const lines: string[] = [
    `# Task: ${ctx.title}`,
    `Client: ${ctx.clientName} (${ctx.clientStack})`,
    "",
  ];

  if (ctx.description) {
    const clean = ctx.description.replace(/<[^>]+>/g, " ").trim().slice(0, 3000);
    lines.push("## Descricao", clean, "");
  }

  if (ctx.comments?.length) {
    lines.push(`## Comentarios (${ctx.comments.length})`);
    for (const c of ctx.comments) {
      lines.push(`**${c.author}** (${c.date?.slice(0, 10)}): ${c.content}`);
    }
    lines.push("");
  }

  if (ctx.figmaUrl) {
    lines.push(
      "## Figma",
      `URL: ${ctx.figmaUrl}`,
      `FileKey: ${ctx.figmaFileKey || "?"} | NodeId: ${ctx.figmaNodeId || "?"}`,
      "Use o MCP Figma (get_design_context e get_screenshot) pra inspecionar o design.",
      ""
    );
  }

  if (ctx.stepsToReproduce) {
    lines.push("## Steps to reproduce", ctx.stepsToReproduce, "");
  }

  if (ctx.stackContext?.rules) {
    lines.push("## Rules da stack", ctx.stackContext.rules, "");
  }

  if (ctx.stackContext?.checklist?.length) {
    lines.push("## Checklist");
    for (const item of ctx.stackContext.checklist) {
      lines.push(`- [ ] ${item}`);
    }
    lines.push("");
  }

  if (ctx.skills?.length) {
    lines.push(`## Skills (${ctx.skills.length})`);
    for (const s of ctx.skills) {
      lines.push(`### ${s.name} (${s.category})`, s.content.slice(0, 3000), "");
    }
  }

  if (ctx.knowledge?.length) {
    lines.push(`## Knowledge (${ctx.knowledge.length})`);
    for (const k of ctx.knowledge) {
      lines.push(
        `### [${k.type}] ${k.title} (confidence: ${k.confidence})`,
        k.content
      );
      if (k.negative) lines.push(`NAO FAZER: ${k.negative}`);
      lines.push("");
    }
  }

  if (ctx.plan?.steps?.length) {
    lines.push("## Plan");
    ctx.plan.steps.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
    if (ctx.plan.files?.length) {
      lines.push(`\nArquivos provaveis: ${ctx.plan.files.join(", ")}`);
    }
    lines.push("");
  }

  if (ctx.memoryContext) {
    lines.push(ctx.memoryContext, "");
  }

  if (ctx.previousTraces) {
    lines.push(ctx.previousTraces, "");
  }

  lines.push(
    "## Instrucoes",
    "- Siga TODAS as rules e o checklist da stack",
    "- ZERO console.log em producao",
    `- Trabalhe APENAS na branch atual (${ctx.branchName})`,
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

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event, _ctx) => {
    const contextFile = process.env.ODUS_CONTEXT_FILE;
    if (!contextFile) return;

    try {
      const raw = readFileSync(contextFile, "utf-8");
      const taskCtx: TaskContext = JSON.parse(raw);
      const extra = buildPrompt(taskCtx);

      return {
        systemPrompt: event.systemPrompt + "\n\n" + extra,
      };
    } catch {
      // Silently fail — orquestrador vai logar o erro
    }
  });
}
