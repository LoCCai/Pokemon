"""网页 AI Agent：OpenAI 兼容 Function Calling + 宝可梦工具。

模型来源（按优先级）：
1. ``POKEMON_LLM_BASE_URL`` / ``POKEMON_LLM_API_KEY`` / ``POKEMON_LLM_MODEL``；
2. 若安装了 MoEllmChats，复用其 ``providers.toml`` 与 ``model_config.json``
   （``POKEMON_LLM_PROVIDER=moellmchats`` 或 ``auto`` 且自身未配置）；
3. 环境变量 ``OPENAI_BASE_URL`` / ``OPENAI_API_KEY`` / ``OPENAI_MODEL``。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore

from ..compat.logger import logger
from .tools import ToolContextData, execute_tool, openai_tool_schemas


@dataclass
class AgentReply:
    text: str = ""
    images: List[str] = field(default_factory=list)
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "images": self.images,
            "tools_used": self.tools_used,
            "provider": self.provider,
            "error": self.error,
        }


def _config():
    try:
        from ..config import plugin_config

        return plugin_config
    except Exception:
        return None


def _moellm_candidates() -> List[Path]:
    paths = []
    try:
        from nonebot_plugin_localstore import get_plugin_data_dir  # type: ignore

        try:
            paths.append(Path(get_plugin_data_dir("nonebot_plugin_moellmchats")))
        except TypeError:
            pass
    except Exception:
        pass
    paths.append(Path.cwd() / "data" / "nonebot_plugin_moellmchats")
    paths.append(Path.cwd() / "data" / "moellmchats")
    return paths


def _read_moellm_endpoint() -> Optional[Tuple[str, str, str]]:
    for root in _moellm_candidates():
        providers = root / "providers.toml"
        model_config = root / "model_config.json"
        if not providers.exists():
            continue
        try:
            data = tomllib.loads(providers.read_text(encoding="utf-8"))
            provider_table = data.get("providers") or {}
            for provider_name, provider in provider_table.items():
                base_url = str(provider.get("base_url") or "").strip()
                api_key = provider.get("api_key")
                if isinstance(api_key, list):
                    api_key = api_key[0] if api_key else ""
                if not base_url or not api_key:
                    continue
                model = ""
                if model_config.exists():
                    cfg = json.loads(model_config.read_text(encoding="utf-8"))
                    selected = str(cfg.get("selected_model") or "")
                    model = selected.split(" (", 1)[0].strip()
                if not model:
                    models = provider.get("models") or []
                    if models:
                        model = str(models[0])
                if model:
                    return base_url, str(api_key), model
        except Exception as exc:
            logger.debug(f"[pokemon] 读取 MoEllmChats 模型配置失败: {exc}")
    return None


def resolve_endpoint() -> Optional[Tuple[str, str, str]]:
    cfg = _config()
    provider = (getattr(cfg, "pokemon_llm_provider", "auto") if cfg else "auto") or "auto"
    if provider == "off":
        return None
    base_url = (getattr(cfg, "pokemon_llm_base_url", "") if cfg else "") or os.getenv("OPENAI_BASE_URL", "")
    api_key = (getattr(cfg, "pokemon_llm_api_key", "") if cfg else "") or os.getenv("OPENAI_API_KEY", "")
    model = (getattr(cfg, "pokemon_llm_model", "") if cfg else "") or os.getenv("OPENAI_MODEL", "")
    if base_url and api_key and model:
        return base_url, api_key, model
    if provider in {"auto", "moellmchats"}:
        found = _read_moellm_endpoint()
        if found:
            return found
    return None


def _system_prompt(ctx: ToolContextData) -> str:
    from ..menu.catalog import build_entries, category_index

    entries = [e for e in build_entries() if not e["pmn_hidden"]]
    categories = category_index(entries)
    lines = []
    for category, items in categories.items():
        names = "、".join(item["func"] for item in items[:14])
        lines.append(f"- {category}：{names}")
    return (
        "你是宝可梦游戏助手，和玩家一起游玩一个宝可梦养成/探索/对战文字游戏。\n"
        "原则：\n"
        "1. 需要游戏数据时优先调用工具，不要编造数值；\n"
        "2. 执行会改变存档的指令（领取、探索、购买、使用道具、战斗）前，先简短说明将做什么；\n"
        "3. 用户要求看图/分析时调用图表工具，并把图片展示出来；\n"
        "4. 战斗和小游戏是连续交互，工具只能发起，后续请提示用户在网页指令面板或聊天里继续；\n"
        "5. 回复简洁、口语化，使用中文。\n\n"
        f"当前玩家：{ctx.user_name}（ID {ctx.user_id}）"
        + (f"，群/房间 {ctx.group_id}" if ctx.group_id else "")
        + "\n\n可用功能分类：\n"
        + "\n".join(lines)
    )


async def _chat_completion(
    endpoint: Tuple[str, str, str],
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    import httpx

    base_url, api_key, model = endpoint
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    cfg = _config()
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(getattr(cfg, "pokemon_llm_temperature", 0.4) if cfg else 0.4),
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    timeout = float(getattr(cfg, "pokemon_llm_timeout", 90.0) if cfg else 90.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"LLM HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 返回空 choices")
    return choices[0].get("message") or {}


async def run_agent(
    message: str,
    ctx: ToolContextData,
    history: Optional[List[Dict[str, str]]] = None,
) -> AgentReply:
    cfg = _config()
    if cfg is not None and not getattr(cfg, "pokemon_llm_enabled", True):
        return AgentReply(text="网页 AI 已在配置中关闭。", error="disabled")

    endpoint = resolve_endpoint()
    if endpoint is None:
        return AgentReply(
            text=(
                "网页 AI 尚未配置模型。请在 `.env` 设置 `POKEMON_LLM_BASE_URL`、"
                "`POKEMON_LLM_API_KEY`、`POKEMON_LLM_MODEL`，或安装并配置 MoEllmChats。\n"
                "你仍然可以使用左侧指令面板直接游玩。"
            ),
            error="no_model",
        )

    base_url, _, model = endpoint
    reply = AgentReply(provider=f"openai-compatible:{model}")
    messages: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt(ctx)}]
    for item in (history or [])[-10:]:
        role = str(item.get("role", "user"))
        content = str(item.get("content", ""))
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    tools = openai_tool_schemas()
    max_steps = int(getattr(cfg, "pokemon_llm_max_steps", 6) if cfg else 6)
    try:
        for _ in range(max(1, max_steps)):
            assistant = await _chat_completion(endpoint, messages, tools)
            tool_calls = assistant.get("tool_calls") or []
            if not tool_calls:
                reply.text = str(assistant.get("content") or "").strip()
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant.get("content") or "",
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                function = call.get("function") or {}
                name = str(function.get("name") or "")
                raw_args = function.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except Exception:
                    arguments = {}
                outcome = await execute_tool(name, arguments, ctx)
                reply.tools_used.append({"name": name, "arguments": arguments, "ok": not outcome.text.startswith("工具执行失败")})
                if outcome.images:
                    reply.images.extend(outcome.images)
                tool_content = outcome.text
                if outcome.structured:
                    try:
                        tool_content += "\n\n[structured]\n" + json.dumps(
                            outcome.structured, ensure_ascii=False, default=str
                        )[:4000]
                    except Exception:
                        pass
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id") or name,
                        "content": tool_content[:8000],
                    }
                )
        else:
            reply.text = "工具调用步数达到上限，请把问题拆小一点再试。"
    except Exception as exc:
        logger.warning(f"[pokemon] 网页 AI 调用失败: {exc}")
        reply.error = str(exc)
        reply.text = f"AI 调用失败：{exc}"
    if not reply.text:
        reply.text = "（模型没有返回文本）"
    return reply


__all__ = ["AgentReply", "resolve_endpoint", "run_agent"]
