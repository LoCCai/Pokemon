from __future__ import annotations

from nonebot_plugin_pokemon.compat.message_models import Button
from nonebot_plugin_pokemon.compat.segment import MessageSegment
from nonebot_plugin_pokemon.platform.message import OutMessage
from nonebot_plugin_pokemon.platform.sender import _qq_build, _v11_build, _v12_build


def _out():
    return OutMessage.coerce(
        [
            MessageSegment.text("你好"),
            MessageSegment.image(b"\x89PNG\r\n\x1a\nfake"),
            MessageSegment.at("12345"),
            MessageSegment.buttons([Button("按钮", "野外探索", "按钮", action=2)]),
        ]
    )


def test_v11_build():
    message = _v11_build(_out(), at_user="999")
    types = [seg.type for seg in message]
    assert types[0] == "at"
    assert "text" in types
    assert "image" in types
    image = next(seg for seg in message if seg.type == "image")
    assert image.data["file"].startswith("base64://")


def test_qq_build():
    message = _qq_build(_out(), at_user="999", user_type="group")
    types = [seg.type for seg in message]
    assert "text" in types
    assert "file_image" in types


async def test_v12_build_text_only(monkeypatch):
    class FakeBot:
        async def call_api(self, *args, **kwargs):
            return {"file_id": "file-1"}

    message = await _v12_build(FakeBot(), OutMessage.coerce("你好"))
    assert [seg.type for seg in message] == ["text"]


def test_out_message_buttons_and_plain_text():
    out = _out()
    assert out.plain_text == "你好"
    assert out.buttons[0].data == "野外探索"
    assert out.text_and_button_hint()
