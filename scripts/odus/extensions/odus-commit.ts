/**
 * Extensao odus-commit
 *
 * Intercepta comandos bash pra:
 * 1. Bloquear git push (o orquestrador faz depois)
 * 2. Bloquear git checkout de outra branch
 * 3. Logar commits feitos
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const BLOCKED_PATTERNS = [
  /git\s+push/,
  /git\s+checkout\s+(?!-b\b)(?!--\b)\S+/, // permite checkout -b (criar branch)
  /gh\s+pr\s+create/,
];

export default function (pi: ExtensionAPI) {
  const branchName = process.env.ODUS_BRANCH_NAME;

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName !== "bash") return;

    const cmd =
      typeof event.input === "string"
        ? event.input
        : (event.input as { command?: string })?.command || "";

    // Bloquear push, checkout de outra branch, PR
    for (const pattern of BLOCKED_PATTERNS) {
      if (pattern.test(cmd)) {
        ctx.ui.notify(
          `Bloqueado: "${cmd.slice(0, 80)}" — o orquestrador controla push e PR`,
          "warn"
        );
        return { block: true, reason: "Bloqueado pelo odus-commit. O orquestrador faz push e PR." };
      }
    }

    // Avisar se tenta mudar de branch
    if (/git\s+checkout\s+-b/.test(cmd) && branchName) {
      ctx.ui.notify(
        `Cuidado: criando sub-branch. Branch principal: ${branchName}`,
        "info"
      );
    }
  });

  // Logar commits
  pi.on("tool_result", async (event, _ctx) => {
    if (event.toolName !== "bash") return;

    const output =
      event.content?.[0]?.type === "text"
        ? (event.content[0] as { text: string }).text
        : "";

    if (output.includes("create mode") || output.includes("files changed")) {
      // Commit detectado — trace vai pegar via odus-trace
    }
  });
}
