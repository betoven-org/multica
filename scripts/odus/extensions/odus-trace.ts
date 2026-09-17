/**
 * Extensao odus-trace
 *
 * Emite eventos pro Trace API a cada tool call e resultado.
 * Trace ID vem via env var ODUS_TRACE_ID.
 * API base vem via env var ODUS_API_BASE.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const API_LOCAL = "http://localhost:3000";

async function apiCall(
  endpoint: string,
  method: string = "POST",
  data?: Record<string, unknown>
): Promise<void> {
  const apiBase = process.env.ODUS_API_BASE || API_LOCAL;
  try {
    const res = await fetch(`${apiBase}${endpoint}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: data ? JSON.stringify(data) : undefined,
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      // Fallback pra prod se local falhou
      if (apiBase === API_LOCAL) {
        await fetch(`https://task.oduscommerce.com.br${endpoint}`, {
          method,
          headers: { "Content-Type": "application/json" },
          body: data ? JSON.stringify(data) : undefined,
          signal: AbortSignal.timeout(10000),
        });
      }
    }
  } catch {
    // Non-blocking — trace e best-effort
  }
}

export default function (pi: ExtensionAPI) {
  const traceId = process.env.ODUS_TRACE_ID;
  if (!traceId) return;

  let toolCallCount = 0;
  const startTime = Date.now();

  // Evento a cada tool call
  pi.on("tool_call", async (event, _ctx) => {
    toolCallCount++;
    await apiCall(`/api/traces/${traceId}/events`, "POST", {
      type: "tool",
      action: event.toolName,
      data: {
        toolCallId: event.toolCallId,
        input:
          typeof event.input === "string"
            ? event.input.slice(0, 500)
            : JSON.stringify(event.input).slice(0, 500),
        sequence: toolCallCount,
      },
    });
  });

  // Evento a cada resultado de tool
  pi.on("tool_result", async (event, _ctx) => {
    if (event.isError) {
      await apiCall(`/api/traces/${traceId}/events`, "POST", {
        type: "error",
        action: `tool_error_${event.toolName}`,
        data: {
          toolCallId: event.toolCallId,
          error: event.content?.[0]?.type === "text"
            ? (event.content[0] as { text: string }).text.slice(0, 500)
            : "unknown",
        },
      });
    }
  });

  // Ao iniciar sessao, registra
  pi.on("session_start", async (_event, _ctx) => {
    await apiCall(`/api/traces/${traceId}/events`, "POST", {
      type: "agent",
      action: "pi_session_started",
      data: { runtime: "pi", version: "0.74.0" },
    });
  });
}
