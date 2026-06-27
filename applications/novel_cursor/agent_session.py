"""Persistent Cursor SDK script / prose agent sessions.

DEPRECATED: cursor_beat.py uses beat_orchestrator (local MCP + stateless LLM).
Kept for reference / manual debugging only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app_config import MODEL, NovelAppConfig
from mcp_config import inline_mcp_servers, repo_root


def _read_agent_id(path: Path) -> str | None:
    if not path.is_file():
        return None
    line = path.read_text(encoding="utf-8").strip().splitlines()
    if line and line[0].strip():
        return line[0].strip()
    return None


def _write_agent_id(path: Path, agent_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(agent_id.strip() + "\n", encoding="utf-8")


def reset_agent_ids(config: NovelAppConfig) -> None:
    for path in (config.script_agent_id_file, config.prose_agent_id_file):
        if path.is_file():
            path.unlink()


def _agent_id_from(agent: Any) -> str:
    for attr in ("agent_id", "agentId", "id"):
        val = getattr(agent, attr, None)
        if val:
            return str(val)
    raise RuntimeError("SDK agent has no agent_id attribute")


async def _collect_run_text(run: Any, *, stream: bool) -> str:
    chunks: list[str] = []
    async for message in run.messages():
        if stream:
            print(message, file=__import__("sys").stderr)
        if getattr(message, "type", None) != "assistant":
            continue
        inner = getattr(message, "message", None)
        if inner is None:
            continue
        for block in getattr(inner, "content", ()) or ():
            if getattr(block, "type", None) == "text":
                chunks.append(getattr(block, "text", "") or "")
    run_result = await run.wait()
    text = "".join(chunks)
    if run_result.status == "error":
        raise RuntimeError(f"SDK run failed: {run_result.id}")
    return text


async def _open_agent(
    client: Any,
    *,
    id_file: Path,
    memnet_session: str,
    primer: str,
    turn_prompt: str,
    stream: bool,
) -> tuple[str, str]:
    from cursor_sdk import AgentOptions, CursorAgentError

    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CURSOR_API_KEY not set")

    mcp = inline_mcp_servers(memnet_session)
    stored = _read_agent_id(id_file)

    async def _create_and_run() -> tuple[str, str]:
        opts = AgentOptions(model=MODEL, api_key=api_key, mcp_servers=mcp)
        agent = await client.agents.create(opts)
        async with agent:
            aid = _agent_id_from(agent)
            primer_run = await agent.send(primer)
            await primer_run.wait()
            run = await agent.send(turn_prompt)
            text = await _collect_run_text(run, stream=stream)
            return text, aid

    if stored:
        try:
            opts = AgentOptions(model=MODEL, api_key=api_key, mcp_servers=mcp)
            agent = await client.agents.resume(stored, opts)
            async with agent:
                run = await agent.send(turn_prompt)
                text = await _collect_run_text(run, stream=stream)
                return text, stored
        except CursorAgentError:
            if id_file.is_file():
                id_file.unlink()

    text, aid = await _create_and_run()
    _write_agent_id(id_file, aid)
    return text, aid


async def run_script_turn(
    client: Any,
    config: NovelAppConfig,
    memnet_session: str,
    primer: str,
    turn_prompt: str,
    *,
    stream: bool = False,
) -> tuple[str, str]:
    return await _open_agent(
        client,
        id_file=config.script_agent_id_file,
        memnet_session=memnet_session,
        primer=primer,
        turn_prompt=turn_prompt,
        stream=stream,
    )


async def run_prose_turn(
    client: Any,
    config: NovelAppConfig,
    memnet_session: str,
    primer: str,
    turn_prompt: str,
    *,
    stream: bool = False,
) -> tuple[str, str]:
    return await _open_agent(
        client,
        id_file=config.prose_agent_id_file,
        memnet_session=memnet_session,
        primer=primer,
        turn_prompt=turn_prompt,
        stream=stream,
    )


async def run_dual_beat_async(
    config: NovelAppConfig,
    memnet_session: str,
    script_prep: dict[str, Any],
    prose_prep: dict[str, Any],
    script_primer: str,
    script_turn: str,
    prose_primer: str,
    prose_turn: str,
    *,
    stream: bool = False,
    script_only: bool = False,
    prose_only: bool = False,
) -> tuple[str, int]:
    from cursor_sdk import AsyncClient, CursorAgentError

    root = repo_root()
    try:
        async with await AsyncClient.launch_bridge(workspace=str(root)) as client:
            if not prose_only:
                await run_script_turn(
                    client,
                    config,
                    memnet_session,
                    script_primer,
                    script_turn,
                    stream=stream,
                )
                if script_only:
                    return "", 0

            text, _ = await run_prose_turn(
                client,
                config,
                memnet_session,
                prose_primer,
                prose_turn,
                stream=stream,
            )
            return text, 0
    except CursorAgentError as err:
        print(f"error: SDK failed: {err.message}", file=__import__("sys").stderr)
        return "", 1
    except RuntimeError as err:
        print(f"error: {err}", file=__import__("sys").stderr)
        return "", 1
