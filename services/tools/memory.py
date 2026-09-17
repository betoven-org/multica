"""
Odus Task — Memory Layer (Mem0)

Memoria persistente entre execucoes do pipeline.
Usa Mem0 com Qdrant local (in-process, sem server externo).

Uso:
  from memory import OdusMemory

  mem = OdusMemory()
  mem.add("VTEX IO nao aceita inline styles", client="cook", stack="VTEX IO")
  results = mem.search("inline styles", client="cook", stack="VTEX IO")
  context = mem.build_context(client="cook", stack="VTEX IO", task_type="layout")
"""
import os
import json
from pathlib import Path

# Mem0 config: Qdrant local (in-process), sem OpenAI (usa keywords)
# Se ANTHROPIC_API_KEY disponivel, usa Claude pra extração de memorias
MEM0_AVAILABLE = False
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    pass

MEMORY_DIR = Path(os.environ.get("ODUS_MEMORY_DIR", str(Path.home() / ".odus" / "memory")))
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _needs_claude_code_llm() -> bool:
    """True se nao tem API key e precisa do Claude Code CLI como LLM."""
    return not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY")


def _get_mem0_config() -> dict:
    """Config do Mem0: Qdrant local + embedder/LLM configuravel."""
    # Embedder define a dimensao dos vetores
    use_openai_embedder = bool(os.environ.get("OPENAI_API_KEY"))
    embedding_dims = 1536 if use_openai_embedder else 384  # OpenAI=1536, MiniLM=384

    config: dict = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "odus_memories",
                "path": str(MEMORY_DIR / "qdrant"),
                "embedding_model_dims": embedding_dims,
            },
        },
    }

    if use_openai_embedder:
        config["embedder"] = {
            "provider": "openai",
            "config": {"model": "text-embedding-3-small"},
        }
    else:
        config["embedder"] = {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dims": embedding_dims,
            },
        }

    # LLM: Mem0 precisa de um pra extrair factos.
    # Se nao tem API key, usamos "ollama" como placeholder e substituimos
    # o self.llm depois do init pelo ClaudeCodeLLM
    if os.environ.get("OPENAI_API_KEY"):
        config["llm"] = {
            "provider": "openai",
            "config": {"model": "gpt-4o-mini", "temperature": 0.1},
        }
    elif os.environ.get("ANTHROPIC_API_KEY"):
        config["llm"] = {
            "provider": "anthropic",
            "config": {"model": "claude-haiku-4-5", "temperature": 0.1},
        }
    else:
        # Placeholder com fake key — sera substituido por ClaudeCodeLLM apos init
        # OpenAI e o unico provider que nao exige lib extra no Mem0
        config["llm"] = {
            "provider": "openai",
            "config": {"model": "gpt-4o-mini", "api_key": "sk-placeholder-will-be-replaced"},
        }

    return config


class OdusMemory:
    """Camada de memoria pra o pipeline Odus Task."""

    def __init__(self):
        self._mem: "Memory | None" = None
        if MEM0_AVAILABLE:
            try:
                self._mem = Memory.from_config(_get_mem0_config())
                # Se nao tem API key, substituir LLM por Claude Code CLI
                if _needs_claude_code_llm():
                    from claude_code_llm import ClaudeCodeLLM
                    self._mem.llm = ClaudeCodeLLM({"model": "haiku"})
            except Exception as e:
                print(f"[mem0] Falhou ao inicializar: {e}")
                self._mem = None

    @property
    def available(self) -> bool:
        return self._mem is not None

    def add(
        self,
        content: str,
        *,
        client: str = "",
        stack: str = "",
        task_type: str = "",
        source: str = "pipeline",
        metadata: dict | None = None,
    ) -> str | None:
        """Adiciona uma memoria. Retorna memory_id ou None."""
        if not self._mem:
            return None

        user_id = self._build_user_id(client, stack)
        meta = {
            "client": client,
            "stack": stack,
            "task_type": task_type,
            "source": source,
            **(metadata or {}),
        }

        try:
            result = self._mem.add(
                content,
                user_id=user_id,
                metadata=meta,
            )
            # Mem0 retorna lista de results
            if isinstance(result, dict) and result.get("results"):
                return result["results"][0].get("id")
            return None
        except Exception as e:
            print(f"[mem0] Erro ao adicionar: {e}")
            return None

    def search(
        self,
        query: str,
        *,
        client: str = "",
        stack: str = "",
        task_type: str = "",
        limit: int = 5,
    ) -> list[dict]:
        """Busca memorias relevantes. Retorna lista de {memory, score, metadata}."""
        if not self._mem:
            return []

        user_id = self._build_user_id(client, stack)

        try:
            results = self._mem.search(
                query,
                filters={"user_id": user_id},
                limit=limit,
            )
            # Normalizar output
            memories = []
            items = results if isinstance(results, list) else results.get("results", [])
            for r in items:
                memories.append({
                    "id": r.get("id", ""),
                    "memory": r.get("memory", ""),
                    "score": r.get("score", 0),
                    "metadata": r.get("metadata", {}),
                })
            return memories
        except Exception as e:
            print(f"[mem0] Erro ao buscar: {e}")
            return []

    def get_all(
        self,
        *,
        client: str = "",
        stack: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """Lista todas as memorias de um client/stack."""
        if not self._mem:
            return []

        user_id = self._build_user_id(client, stack)

        try:
            results = self._mem.get_all(filters={"user_id": user_id})
            items = results if isinstance(results, list) else results.get("results", [])
            return items[:limit]
        except Exception as e:
            print(f"[mem0] Erro ao listar: {e}")
            return []

    def build_context(
        self,
        *,
        client: str = "",
        stack: str = "",
        task_type: str = "",
        task_title: str = "",
        limit: int = 10,
    ) -> str:
        """Monta bloco de contexto com memorias relevantes pra injetar no prompt."""
        if not self._mem:
            return ""

        # Buscar por relevancia ao titulo da task
        query = f"{task_type} {stack} {task_title}".strip()
        if not query:
            return ""

        memories = self.search(
            query,
            client=client,
            stack=stack,
            task_type=task_type,
            limit=limit,
        )

        if not memories:
            return ""

        lines = [
            f"## Memoria do Pipeline ({len(memories)} items relevantes)",
            "Aprendizados de execucoes anteriores. Use como referencia.",
            "",
        ]

        for m in memories:
            source = m.get("metadata", {}).get("source", "?")
            lines.append(f"- [{source}] {m['memory']}")

        return "\n".join(lines)

    def learn_from_execution(
        self,
        *,
        client: str,
        stack: str,
        task_type: str,
        task_title: str,
        # Evidencia
        human_intervention: bool = False,
        review_rejected: bool = False,
        verify_failed: bool = False,
        qa_failed: bool = False,
        # Contexto
        files_changed: list[str] | None = None,
        issues: list[str] | None = None,
        human_diff: str = "",
    ) -> list[str]:
        """Extrai memorias de uma execucao. So grava com evidencia.
        Retorna lista de memory_ids criados."""
        if not self._mem:
            return []

        # SEM evidencia = SEM memoria (principio central)
        if not (human_intervention or review_rejected or verify_failed or qa_failed):
            return []

        created: list[str] = []
        reason = ""
        if human_intervention:
            reason = "intervencao humana"
        elif review_rejected:
            reason = "review rejeitou"
        elif verify_failed:
            reason = "verify falhou"
        elif qa_failed:
            reason = "QA falhou"

        # Memorias dos issues do reviewer
        if issues:
            for issue in issues[:5]:
                mid = self.add(
                    f"[{stack}] {issue}",
                    client=client,
                    stack=stack,
                    task_type=task_type,
                    source=f"evidence:{reason}",
                    metadata={"task_title": task_title},
                )
                if mid:
                    created.append(mid)

        # Memoria do diff humano
        if human_diff:
            mid = self.add(
                f"[{stack}] Correcao humana em {task_title}: {human_diff[:500]}",
                client=client,
                stack=stack,
                task_type=task_type,
                source="human_correction",
                metadata={"task_title": task_title},
            )
            if mid:
                created.append(mid)

        # Memoria generica do problema
        if not created:
            mid = self.add(
                f"[{stack}] Task '{task_title}' teve problema: {reason}. Arquivos: {', '.join(files_changed or [])}",
                client=client,
                stack=stack,
                task_type=task_type,
                source=f"evidence:{reason}",
                metadata={"task_title": task_title},
            )
            if mid:
                created.append(mid)

        return created

    @staticmethod
    def _build_user_id(client: str, stack: str) -> str:
        """user_id = chave de particionamento no Mem0."""
        parts = [p for p in [client.lower().replace(" ", "-"), stack.lower().replace(" ", "-")] if p]
        return ":".join(parts) if parts else "global"
