from __future__ import annotations

from nonebot_plugin_pokemon.compat.models import Event
from nonebot_plugin_pokemon.compat.sv import SV
from nonebot_plugin_pokemon.matchers.dispatcher import _permission_ok
from nonebot_plugin_pokemon.platform.ingress import clean_text


def test_command_without_space():
    found = SV.find("精灵图鉴皮卡丘")
    assert found is not None
    trigger, arg = found
    assert trigger.keyword == "精灵图鉴"
    assert arg == "皮卡丘"


def test_command_with_space():
    trigger, arg = SV.find("精灵图鉴 皮卡丘")
    assert trigger.keyword == "精灵图鉴"
    assert arg == "皮卡丘"


def test_fullmatch():
    trigger, arg = SV.find("野外探索")
    assert trigger.type == "fullmatch"
    assert arg == ""


def test_prefix():
    trigger, arg = SV.find("前往1号道路")
    assert trigger.type == "prefix"
    assert arg == "1号道路"


def test_longer_keyword_wins():
    trigger, _ = SV.find("领取初始精灵小火龙")
    assert trigger.keyword == "领取初始精灵"


def test_clean_text_strips_command_start_and_at_tag():
    assert clean_text("/精灵状态 皮卡丘") == "精灵状态 皮卡丘"
    assert clean_text("<@!123> 精灵状态 皮卡丘") == "精灵状态 皮卡丘"
    assert clean_text("　 野外探索  ") == "野外探索"


def test_superuser_permission():
    ev = Event(user_id="super-1", sender={"role": "member"})
    trigger = next(t for t in SV.all_triggers() if t.sv.pm == 0)
    assert _permission_ok(ev, trigger)


def test_member_cannot_use_admin_command():
    ev = Event(user_id="normal", sender={"role": "member"})
    trigger = next(t for t in SV.all_triggers() if t.sv.pm == 0)
    assert not _permission_ok(ev, trigger)


def test_group_owner_can_use_group_command():
    ev = Event(user_id="owner", sender={"role": "owner"})
    trigger = next(t for t in SV.all_triggers() if t.sv.pm == 2) if any(
        t.sv.pm == 2 for t in SV.all_triggers()
    ) else None
    if trigger is not None:
        assert _permission_ok(ev, trigger)
