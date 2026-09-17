"""
Custom LLM provider pro Mem0 que usa Claude Code CLI.
Nao precisa de API key — usa a sessao do Claude Max/Pro.

Uso:
  config = {
      "llm": {
          "provider": "custom",
          "config": {"model": "haiku"},
      },
  }

  # Registrar antes de criar Memory
  from claude_code_llm import ClaudeCodeLLM
  # Mem0 aceita custom LLM via classe direta
"""
import json
import re
import subprocess
from typing import Dict, List, Optional


class ClaudeCodeLLM:
    """LLM provider que usa `claude -p` via CLI."""

    def __init__(self, config=None):
        self.model = "haiku"
        if config:
            if hasattr(config, "model") and config.model:
                self.model = config.model
            elif isinstance(config, dict) and config.get("model"):
                self.model = config["model"]

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs,
    ) -> str:
        """Converte messages pra prompt e roda claude -p."""
        # Montar prompt a partir das messages
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.insert(0, content)
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"[Resposta anterior]: {content}")

        prompt = "\n\n".join(prompt_parts)

        # Se tem tools, pedir JSON structured
        if tools:
            tool_names = [t.get("function", {}).get("name", t.get("name", "?")) for t in tools]
            prompt += f"\n\nResponda APENAS em JSON valido. Tools disponiveis: {tool_names}"

        try:
            result = subprocess.run(
                ["claude", "-p", "--model", self.model, prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            response = result.stdout.strip()

            if not response:
                return ""

            # Se tinha tools, tentar parsear como tool call
            if tools:
                return self._parse_tool_response(response, tools)

            return response

        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            return ""
        except Exception:
            return ""

    def _parse_tool_response(self, response: str, tools: List[Dict]) -> str | dict:
        """Tenta extrair tool call do response se o Mem0 pediu."""
        # Mem0 as vezes pede tool calls pra structured extraction
        # Tentar parsear JSON
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                # Se parece um tool call, formatar como Mem0 espera
                if "tool_calls" in str(tools[0]) if tools else False:
                    return {
                        "content": response,
                        "tool_calls": [{
                            "name": tools[0].get("function", {}).get("name", ""),
                            "arguments": parsed,
                        }],
                    }
                return response
            except json.JSONDecodeError:
                pass

        return response
