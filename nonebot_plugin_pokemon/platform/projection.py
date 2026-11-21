"""Safe passive projection of real core game output for QWeb sessions.

This module never plays the game and never re-implements battle formulas. It only
observes the messages/buttons the real core handlers already produced and turns
them into semantic session state:

* combatant names/levels exactly as printed by the core;
* the real clickable move buttons (``技能(pp/ppmax)`` -> plain core move name);
* semantic events such as encounter / deploy / turn / move / result;
* the legal clickable options for the current waiting interaction.

Anything the core did not emit (for example exact remaining HP in the automatic
battle text path) is left absent instead of being guessed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from ..Pokemon.pokemon_duel.pokeconfg import JINENG_LIST

_MOVE_BUTTON = re.compile(r"^(?P<name>.+?)\((?P<pp>\d+)/(?P<ppmax>\d+)\)$")
_LEVEL = re.compile(r"(?P<name>[^\n]{1,60}?)\s*Lv\.(?P<level>\d+)")
_ENCOUNTER = re.compile(r"野生宝可梦(?P<name>[^\s，,。]+?)(?P<group>群)?出现了")
_TRAINER = re.compile(r"(?:向|和)(?P<name>[^\n，,。]{1,40}?)(?:发起了|进行)")
_ROUND = re.compile(r"回合[：:]\s*(?P<round>\d+)")
_USED_MOVE = re.compile(r"(?P<name>[^\n，,。]{1,30}?)使用了技能(?P<move>[^\n，,。]+)")
_WON = re.compile(r"(?P<winner>[^\n，,。>]{1,60}?)战胜了(?P<loser>[^\n，,。>]{1,60})")
_HP = re.compile(r"(?:血量|HP)[：:]\s*(?P<hp>\d+)(?:\s*/\s*(?P<max>\d+))?")

_BATTLE_CHOICES = {
    "mega进化",
    "替换精灵",
    "试炼逃跑",
    "逃跑",
    "挣扎",
    "捕捉",
    "拒绝捕捉",
    "接受对战",
    "拒绝对战",
    "同意对战",
    "取消对战",
}

_CONFIRM_CHOICES = {"捕捉", "拒绝捕捉", "接受对战", "拒绝对战", "同意对战", "取消对战"}

_CHALLENGE_ACTIONS = {
    "挑战道馆": ("gym", "道馆"),
    "挑战天王": ("elite", "天王"),
    "挑战四天王冠军": ("champion", "冠军"),
    "挑战冠军": ("champion", "冠军"),
    "首领挑战": ("boss", "首领"),
    "世界boss挑战": ("world_boss", "世界首领"),
    "挑战试炼塔": ("tower", "试炼塔"),
    "挑战精灵塔": ("tower", "试炼塔"),
}

_NON_AWAITING_ACTIONS = {
    "野外探索": ("explore", None, "探索"),
    "野外垂钓": ("fish", None, "垂钓"),
}

_LIMIT_EVENTS = 40


def empty_state() -> Dict[str, Any]:
    return {
        "battle": None,
        "events": [],
        "last_text": "",
        "seq": 0,
    }


def _event(state: Dict[str, Any], kind: str, **data: Any) -> None:
    state["seq"] = int(state.get("seq") or 0) + 1
    event = {"id": state["seq"], "type": kind}
    event.update({key: value for key, value in data.items() if value is not None})
    events = state.setdefault("events", [])
    events.append(event)
    if len(events) > _LIMIT_EVENTS:
        del events[: len(events) - _LIMIT_EVENTS]


def _battle(state: Dict[str, Any]) -> Dict[str, Any]:
    battle = state.get("battle")
    if not isinstance(battle, dict):
        battle = {}
        state["battle"] = battle
    battle.setdefault("active", False)
    battle.setdefault("round", 0)
    battle.setdefault("player", None)
    battle.setdefault("opponent", None)
    battle.setdefault("moves", [])
    battle.setdefault("result", "")
    battle.setdefault("source", "core-output")
    return battle


def observe_message(state: Dict[str, Any], message: Any) -> None:
    """Project one real ``OutMessage`` into ``state`` (in place)."""

    text = str(getattr(message, "plain_text", "") or "")
    if text:
        _observe_text(state, text)
    try:
        buttons = list(getattr(message, "buttons", []) or [])
    except Exception:
        buttons = []
    if buttons:
        moves = _move_buttons(buttons)
        if moves:
            battle = _battle(state)
            battle["moves"] = [move["value"] for move in moves]
            battle["active"] = True
            _event(state, "battle.options", moves=[move["value"] for move in moves])
    state["last_text"] = text


def _observe_text(state: Dict[str, Any], text: str) -> None:
    battle = _battle(state)

    match = _ENCOUNTER.search(text)
    if match:
        name = match.group("name")
        group = bool(match.group("group"))
        battle["opponent"] = {"name": name, **({"group": True} if group else {})}
        battle["active"] = True
        battle["result"] = ""
        _event(state, "battle.encounter", opponent=name, group=group or None)

    match = _TRAINER.search(text)
    if match and ("对战" in text or "挑战" in text):
        name = match.group("name").strip()
        if name and not battle.get("opponent"):
            battle["opponent"] = {"name": name}
            battle["active"] = True
            _event(state, "battle.opponent", opponent=name)

    for line in text.splitlines():
        match = _LEVEL.search(line)
        if not match:
            continue
        name = match.group("name").strip(" ：:>")
        if not name:
            continue
        level = int(match.group("level"))
        if "派出了" in line or "派出" in line:
            side = "opponent" if any(word in line for word in ("敌方", "对手", "对方")) else "player"
            old = battle.get(side) or {}
            if old.get("name") != name or old.get("level") != level:
                if side == "opponent":
                    battle["opponent"] = {"name": name, "level": level}
                else:
                    battle["player"] = {"name": name, "level": level}
                battle["active"] = True
                _event(state, f"battle.deploy.{side}", name=name, level=level)
        elif "野生宝可梦" in line or "试炼精灵" in line:
            if (battle.get("opponent") or {}).get("name") != name:
                battle["opponent"] = {"name": name, "level": level}
                battle["active"] = True
                _event(state, "battle.deploy.opponent", name=name, level=level)

    match = _ROUND.search(text)
    if match:
        battle["round"] = int(match.group("round"))
        battle["active"] = True
        _event(state, "battle.turn", round=battle["round"])

    match = _USED_MOVE.search(text)
    if match:
        move = match.group("move").strip()
        actor = match.group("name").strip()
        battle["active"] = True
        _event(state, "battle.move", actor=actor, move=move)

    match = _HP.search(text)
    if match:
        hp = int(match.group("hp"))
        max_hp = int(match.group("max")) if match.group("max") else None
        _event(state, "battle.hp", hp=hp, max_hp=max_hp)

    match = _WON.search(text)
    if match:
        winner = match.group("winner").strip()
        loser = match.group("loser").strip()
        if battle.get("active"):
            battle["result"] = f"{winner}战胜了{loser}"
            battle["active"] = False
            _event(state, "battle.result", winner=winner, loser=loser)


def _move_buttons(buttons: Iterable[Any]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for button in buttons:
        data = str(getattr(button, "data", None) or getattr(button, "text", "") or "")
        match = _MOVE_BUTTON.match(data)
        name = match.group("name") if match else data
        info = JINENG_LIST.get(name)
        if not info:
            continue
        item = {
            "value": name,
            "label": str(getattr(button, "text", "") or data),
            "type": info[0],
            "damage_class": info[1],
            "power": info[2],
        }
        if match:
            item["pp"] = int(match.group("pp"))
            item["pp_max"] = int(match.group("ppmax"))
        result.append(item)
    return result


def option_from_button(button: Any, *, awaiting: bool, battle: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    data = str(getattr(button, "data", None) or getattr(button, "text", "") or "").strip()
    if not data:
        return None
    label = str(getattr(button, "text", "") or data)
    pressed = getattr(button, "pressed_text", None)

    if awaiting:
        match = _MOVE_BUTTON.match(data)
        name = match.group("name") if match else data
        if name in JINENG_LIST:
            info = JINENG_LIST[name]
            move = {
                "name": name,
                "type": info[0],
                "damage_class": info[1],
                "power": info[2],
            }
            if match:
                move["pp"] = int(match.group("pp"))
                move["pp_max"] = int(match.group("ppmax"))
            return {
                "id": f"reply:{name}",
                "action": "reply",
                "value": name,
                "data": data,
                "label": label,
                "kind": "move",
                "move": move,
            }
        kind = "confirm" if data in _CONFIRM_CHOICES else ("battle" if data in _BATTLE_CHOICES else "reply")
        return {
            "id": f"reply:{data}",
            "action": "reply",
            "value": data,
            "data": data,
            "label": label,
            "pressed_text": pressed,
            "kind": kind,
        }

    if data in _NON_AWAITING_ACTIONS:
        action, value, kind_label = _NON_AWAITING_ACTIONS[data]
        return {
            "id": f"{action}:{value or ''}",
            "action": action,
            "value": value,
            "data": data,
            "label": label,
            "kind": kind_label,
        }
    if data in _CHALLENGE_ACTIONS:
        value, kind_label = _CHALLENGE_ACTIONS[data]
        return {
            "id": f"challenge:{value}",
            "action": "challenge",
            "value": value,
            "data": data,
            "label": label,
            "kind": kind_label,
        }
    return None


def extract_options(messages: Iterable[Any], *, awaiting: bool) -> List[Dict[str, Any]]:
    """Return legal clickable options from the latest real core buttons."""

    latest: List[Any] = []
    for message in messages:
        buttons = list(getattr(message, "buttons", []) or [])
        if buttons:
            latest = buttons
    result: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for button in latest:
        option = option_from_button(button, awaiting=awaiting)
        if option is None:
            continue
        key = (str(option.get("action")), str(option.get("value")))
        if key in seen:
            continue
        seen.add(key)
        result.append(option)
    if awaiting:
        cancel_key = ("cancel", "")
        if cancel_key not in seen:
            result.append({"id": "cancel", "action": "cancel", "value": None, "label": "取消", "kind": "cancel"})
    return result


def accepted_reply_values(messages: Iterable[Any]) -> Dict[str, str]:
    """Map every legal core reply spelling to the value the core actually accepts."""

    latest: List[Any] = []
    for message in messages:
        buttons = list(getattr(message, "buttons", []) or [])
        if buttons:
            latest = buttons
    mapping: Dict[str, str] = {}
    for button in latest:
        data = str(getattr(button, "data", None) or getattr(button, "text", "") or "").strip()
        if not data:
            continue
        mapping[data] = data
        text = str(getattr(button, "text", "") or "")
        if text:
            mapping.setdefault(text, data)
        pressed = getattr(button, "pressed_text", None)
        if pressed:
            mapping.setdefault(str(pressed), data)
        match = _MOVE_BUTTON.match(data)
        if match and match.group("name") in JINENG_LIST:
            mapping[match.group("name")] = match.group("name")
    return mapping


def build_state(
    projection: Optional[Dict[str, Any]],
    *,
    operation: str,
    turn: int,
    awaiting: bool,
    done: bool,
    error: str = "",
    battle_view: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    projection = projection or empty_state()
    battle = projection.get("battle")
    if isinstance(battle, dict):
        battle = dict(battle)
        battle["moves"] = list(battle.get("moves") or [])
    else:
        battle = None
    # The core manual-turn hook (game.web_turn.project_round) writes the real
    # combatants' HP/level/id/name. Prefer it whenever it exists; the passive
    # text projection is only a fallback for output the core did not annotate.
    if battle_view:
        battle = dict(battle_view)
        battle.setdefault("source", "core")
        if not battle.get("moves") and isinstance(projection.get("battle"), dict):
            battle["moves"] = list((projection.get("battle") or {}).get("moves") or [])
    elif isinstance(battle, dict) and battle:
        battle.setdefault("source", "core-output")
    return {
        "phase": "awaiting" if awaiting else ("error" if error else ("done" if done else "running")),
        "operation": operation,
        "turn": int(turn),
        "awaiting": bool(awaiting),
        "done": bool(done),
        "battle": battle,
        "events": list(projection.get("events") or [])[-20:],
    }


__all__ = [
    "accepted_reply_values",
    "build_state",
    "empty_state",
    "extract_options",
    "observe_message",
    "option_from_button",
]
