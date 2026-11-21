from __future__ import annotations

import json

from nonebot_plugin_pokemon.compat.sv import SV
from nonebot_plugin_pokemon.menu import external_menu, menu_data
from nonebot_plugin_pokemon.menu.catalog import build_entries, category_index, search_entries


def test_every_registered_handler_has_menu_entry():
    entries = build_entries()
    covered = {entry["handler"] for entry in entries}
    handlers = {f"{t.func.__module__}.{t.func.__name__}" for t in SV.all_triggers()}
    missing = handlers - covered
    assert not {"wsid", "虚拟id"} & {t.keyword for t in SV.all_triggers()}
    assert all("早柚" not in t.keyword for t in SV.all_triggers())
    assert not missing, f"菜单缺少处理器: {sorted(missing)}"


def test_menu_entries_have_required_fields():
    for entry in build_entries():
        assert entry["func"]
        assert entry["trigger_method"]
        assert entry["trigger_condition"]
        assert entry["brief_des"]
        assert entry["detail_des"]
        assert entry["category"] in category_index()
        assert entry["triggers"]
        for trigger in entry["triggers"]:
            assert trigger["type"] in {"fullmatch", "command", "prefix", "regex", "keyword"}
            assert trigger["value"]


def test_menu_data_intents_are_bounded():
    data = menu_data()
    assert len(data) >= 90
    for item in data:
        assert isinstance(item["pmn_hidden"], bool)
        intents = item["llm_intents"]
        assert len(intents) <= 16
        for intent in intents:
            assert 4 <= len(intent) <= 80, intent


def test_external_menu_is_picmenu_schema_compatible():
    menu = external_menu()
    assert menu["name"] == "宝可梦"
    assert menu["supported_adapters"] == ["~onebot.v11", "~onebot.v12", "~qq"]
    assert menu["funcs"]
    for func in menu["funcs"]:
        assert set(func) <= {
            "func",
            "trigger_method",
            "trigger_condition",
            "brief_des",
            "detail_des",
            "pmn_hidden",
        }
        assert set(func) >= {"func", "trigger_method", "trigger_condition", "brief_des", "detail_des"}
    json.dumps(menu, ensure_ascii=False)
    # 严格 Schema 不允许 llm_intents 等私有字段
    assert "llm_intents" not in json.dumps(menu)


def test_external_menu_matches_picmenu_schema():
    jsonschema = __import__("pytest").importorskip("jsonschema")
    from pathlib import Path

    schema = json.loads(
        (Path(__file__).parent / "fixtures" / "picmenu_external_schema.json").read_text(encoding="utf-8")
    )
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(external_menu()))
    assert not errors, [error.message for error in errors[:5]]


def test_menu_search():
    assert search_entries("对战")
    assert search_entries("初始精灵")
    assert search_entries("不存在的功能xyz") == []


def test_categories_sorted():
    categories = list(category_index())
    assert categories[0] == "基础"
    assert "管理" in categories
