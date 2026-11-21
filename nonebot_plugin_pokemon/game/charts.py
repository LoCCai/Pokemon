"""游戏数据图表（matplotlib，无显示后端）。"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_FONT_PATH = Path(__file__).resolve().parent.parent / "Pokemon" / "utils" / "fonts" / "starrail_origin.ttf"
_style_ready = False


def _setup_style() -> None:
    global _style_ready
    if _style_ready:
        return
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager, rcParams

    if _FONT_PATH.exists():
        try:
            font_manager.fontManager.addfont(str(_FONT_PATH))
            name = font_manager.FontProperties(fname=str(_FONT_PATH)).get_name()
            rcParams["font.family"] = [name, "DejaVu Sans"]
        except Exception:
            rcParams["font.family"] = ["DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False
    rcParams["figure.facecolor"] = "#0f1420"
    rcParams["axes.facecolor"] = "#161d2c"
    rcParams["axes.edgecolor"] = "#31405c"
    rcParams["axes.labelcolor"] = "#dfe8ff"
    rcParams["text.color"] = "#dfe8ff"
    rcParams["xtick.color"] = "#aebbd6"
    rcParams["ytick.color"] = "#aebbd6"
    rcParams["grid.color"] = "#26324a"
    _style_ready = True


def _finish(fig: Any) -> bytes:
    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=130, facecolor=fig.get_facecolor())
    buffer.seek(0)
    data = buffer.read()
    import matplotlib.pyplot as plt

    plt.close(fig)
    return data


def _empty(message: str = "暂无数据") -> bytes:
    _setup_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=16)
    ax.axis("off")
    return _finish(fig)


def team_radar(analysis: Dict[str, Any], title: str = "队伍平均能力") -> bytes:
    _setup_style()
    import numpy as np
    import matplotlib.pyplot as plt

    averages = analysis.get("average_stats") or {}
    labels = ["HP", "物攻", "物防", "特攻", "特防", "速度"]
    values = [float(averages.get(label, 0)) for label in labels]
    if not any(values):
        return _empty("暂无队伍数据")
    max_value = max(values) * 1.15 or 1.0
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5.6, 5.0), subplot_kw={"polar": True})
    ax.plot(angles, values, color="#5da8ff", linewidth=2)
    ax.fill(angles, values, color="#5da8ff", alpha=0.28)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max_value)
    ax.set_title(title, pad=18, fontsize=15)
    ax.grid(color="#34466b")
    return _finish(fig)


def bar_chart(
    labels: List[str],
    values: List[float],
    title: str,
    *,
    horizontal: bool = False,
    color: str = "#5da8ff",
    ylabel: str = "",
) -> bytes:
    if not labels or not values:
        return _empty()
    _setup_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, max(3.2, 0.42 * len(labels) + 2.0)))
    if horizontal:
        bars = ax.barh(labels, values, color=color)
        ax.invert_yaxis()
        ax.set_xlabel(ylabel or "数值")
        ax.bar_label(bars, fmt="%.0f", padding=3, color="#dfe8ff")
    else:
        bars = ax.bar(labels, values, color=color)
        ax.set_ylabel(ylabel or "数值")
        ax.bar_label(bars, fmt="%.0f", padding=3, color="#dfe8ff")
        plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    ax.set_title(title, fontsize=15, pad=12)
    ax.grid(axis="y" if not horizontal else "x", alpha=0.35, linestyle="--")
    for spine in ax.spines.values():
        spine.set_color("#31405c")
    return _finish(fig)


def pie_chart(labels: List[str], values: List[float], title: str) -> bytes:
    if not labels or not values:
        return _empty()
    _setup_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    colors = ["#5da8ff", "#7de2c3", "#ffd166", "#ff8fab", "#c3a6ff", "#ffa94d", "#74c0fc", "#b2f2bb"]
    ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=120,
        colors=colors[: len(labels)],
        textprops={"color": "#dfe8ff"},
        wedgeprops={"edgecolor": "#0f1420", "linewidth": 1.5},
    )
    ax.set_title(title, fontsize=15)
    ax.axis("equal")
    return _finish(fig)


def line_chart(x: List[float], y: List[float], title: str, xlabel: str, ylabel: str) -> bytes:
    if not x or not y:
        return _empty()
    _setup_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(x, y, color="#7de2c3", linewidth=2.2, marker="o", markersize=3.5)
    ax.fill_between(x, y, color="#7de2c3", alpha=0.18)
    ax.set_title(title, fontsize=15)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3, linestyle="--")
    return _finish(fig)


def team_charts(profile: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, bytes]:
    team = profile.get("team") or []
    charts: Dict[str, bytes] = {}
    charts["team_radar"] = team_radar(
        analysis,
        f"{profile.get('nickname', '训练家')} · 队伍平均能力",
    )
    charts["team_levels"] = bar_chart(
        [item.get("name", "?") for item in team],
        [int(item.get("level", 0)) for item in team],
        "队伍等级",
        ylabel="等级",
    )
    type_counter: Dict[str, int] = {}
    for item in team:
        for type_name in item.get("types", []):
            type_counter[type_name] = type_counter.get(type_name, 0) + 1
    charts["team_types"] = pie_chart(list(type_counter), list(type_counter.values()), "队伍属性分布")
    return charts


def global_charts(overview: Dict[str, Any]) -> Dict[str, bytes]:
    top = overview.get("top_species") or []
    charts: Dict[str, bytes] = {}
    charts["popular_species"] = bar_chart(
        [item["name"] for item in top],
        [item["count"] for item in top],
        "热门宝可梦（全服持有数）",
        horizontal=True,
        color="#7de2c3",
        ylabel="持有数",
    )
    distribution = overview.get("level_distribution") or []
    charts["level_distribution"] = line_chart(
        [item["level"] for item in distribution],
        [item["count"] for item in distribution],
        "全服等级分布",
        "等级",
        "数量",
    )
    return charts


def to_data_url(data: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


__all__ = [
    "bar_chart",
    "global_charts",
    "line_chart",
    "pie_chart",
    "team_charts",
    "team_radar",
    "to_data_url",
]
