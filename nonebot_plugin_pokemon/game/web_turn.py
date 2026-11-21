"""Manual move selection during a native QWeb encounter.

The encounter, damage, turn order and rewards continue to run in the game engine.
The scoped context is inherited only by tasks started from the native action route.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from ..compat.message_models import Button

turn_bot: ContextVar[Any] = ContextVar("pokemon_web_turn_bot", default=None)


def project_round(player: list, opponent: list, number: int, finished: bool = False) -> None:
    bot = turn_bot.get()
    if bot is None:
        return

    def fighter(row: list) -> dict:
        return {
            "id": int(row[18]), "name": str(row[0]), "level": int(row[2]),
            "hp": max(0, int(row[17])), "max_hp": int(row[3]),
        }

    bot.transport.battle_view = {
        "player": fighter(player), "opponent": fighter(opponent),
        "round": number, "finished": finished,
    }


async def choose_move(player: list, opponent: list, moves: list[str], number: int, history: str) -> str:
    bot = turn_bot.get()
    project_round(player, opponent, number)
    choices = [Button(move, move, action=1) for move in dict.fromkeys(moves) if move]
    response = await bot.receive_resp(history[-600:] or "选择招式", choices, timeout=90)
    if response is None or response.text not in {button.data for button in choices}:
        raise ValueError("这次战斗选择已失效，请重新探索。")
    return response.text
