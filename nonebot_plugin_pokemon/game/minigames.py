"""Adapt QWeb personal rounds to the five native group quiz handlers."""

from __future__ import annotations

from typing import Any, Optional

MINIGAME_GAMES = ("我是谁", "猜图鉴", "猜技能", "猜属性", "猜精灵")
HINT_GAMES = frozenset({"猜技能", "猜属性", "猜精灵"})


def canonical_game(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value in MINIGAME_GAMES else None


def scope_for(user_id: str) -> str:
    return f"web-minigame:{user_id}"


def normalize_guess(value: Any, game: str = "") -> str:
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        value = " ".join(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("请输入本轮答案。")
    if len(value) > 100:
        raise ValueError("答案最多 100 个字。")
    if game == "猜属性":
        from ..Pokemon.pokemon_whois import listshuxing

        parts = value.split()
        if len(set(parts)) != 2 or len(parts) != 2 or not set(parts).issubset(listshuxing):
            raise ValueError("请选择两种不同的属性。")
    return value.strip()


def judges():
    from ..Pokemon import pokemon_whois as games

    return (
        games.winner_judger,
        games.winner_judger_cc,
        games.winner_judger_jn,
        games.winner_judger_sx,
        games.winner_judger_tj,
    )


def reset_scope(scope: str) -> None:
    # A native judge retains the reveal image even after turn_off. Discard only
    # entries for this web player when the round finishes, times out or exits.
    if scope:
        for judge in judges():
            for values in vars(judge).values():
                if isinstance(values, dict):
                    values.pop(scope, None)


def build_view(messages, *, game: str, awaiting: bool, done: bool) -> dict:
    texts = (
        [message.plain_text for message in messages if message.plain_text and not message.plain_text.startswith("请在")]
        if game
        else []
    )
    hints = [text for text in texts if text.startswith("提示")]
    phase = "idle" if not game else "done" if done else "awaiting" if awaiting else "running"
    options = []
    if phase == "awaiting":
        options.append({"action": "minigame_guess", "label": "猜一下", "kind": "guess", "accepts": "text"})
        if game in HINT_GAMES:
            options.append({"action": "minigame_hint", "label": "已公布的提示", "kind": "hint"})
        options.append({"action": "cancel", "label": "退出猜题", "kind": "cancel"})
    elif phase == "running":
        options.append({"action": "cancel", "label": "退出猜题", "kind": "cancel"})
    else:
        options.extend({"action": "minigame_start", "value": name, "label": name} for name in MINIGAME_GAMES)
    view = {
        "game": game,
        "phase": phase,
        "hints": hints,
        "hint_available": game in HINT_GAMES,
        "prompt": texts[-1] if texts else "",
        "allowed_actions": options,
    }
    if game == "猜属性":
        from ..Pokemon.pokemon_whois import listshuxing

        view["types"] = listshuxing
    return view
