"""出站发送：把统一消息转换成各协议消息并记录可回放结果。"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from ..compat.gss import gss
from ..compat.logger import logger
from .ingress import adapter_kind
from .message import OutMessage, Segment


@dataclass
class SendResult:
    ok: bool = True
    text: str = ""
    images: List[bytes] = field(default_factory=list)
    buttons: List[Any] = field(default_factory=list)
    error: str = ""
    raw: Any = None

    @classmethod
    def from_message(cls, out: OutMessage, ok: bool = True, raw: Any = None) -> "SendResult":
        return cls(
            ok=ok,
            text=out.plain_text,
            images=[img for img in out.images if isinstance(img, (bytes, bytearray))],
            buttons=out.buttons,
            raw=raw,
        )


def _image_ref(data: Any) -> str:
    if isinstance(data, str):
        return data
    raw = bytes(data)
    return "base64://" + base64.b64encode(raw).decode()


def _v11_build(out: OutMessage, at_user: str = "") -> Any:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    message = Message()
    if at_user:
        message += MessageSegment.at(at_user)
    for seg in out.segments:
        if seg.type == "text":
            message += MessageSegment.text(str(seg.data))
        elif seg.type == "image":
            message += MessageSegment.image(_image_ref(seg.data))
        elif seg.type == "at":
            message += MessageSegment.at(str(seg.data))
        elif seg.type in {"record", "video", "file"}:
            # 游戏当前不发送这些类型；保留文本占位避免崩溃
            message += MessageSegment.text(f"[{seg.type}]")
    if not message:
        message += MessageSegment.text(out.plain_text or "（空消息）")
    return message


async def _v12_image(bot: Any, data: Any) -> Optional[str]:
    if isinstance(data, str) and data.startswith(("http://", "https://")):
        return data
    raw = bytes(data) if not isinstance(data, str) else base64.b64decode(data[9:])
    payload = base64.b64encode(raw).decode()
    name = f"pokemon_{uuid.uuid4().hex[:12]}.jpg"
    try:
        result = await bot.call_api(
            "upload_file",
            type="image",
            name=name,
            data=payload,
        )
        if isinstance(result, dict):
            file_id = result.get("file_id") or result.get("id")
        else:
            file_id = result
        if file_id:
            return str(file_id)
    except Exception as exc:
        logger.debug(f"[pokemon] OneBot v12 图片上传失败: {exc}")
    return None


async def _v12_build(bot: Any, out: OutMessage, at_user: str = "") -> Any:
    from nonebot.adapters.onebot.v12 import Message, MessageSegment

    message = Message()
    if at_user:
        message += MessageSegment.mention(at_user) + " "
    for seg in out.segments:
        if seg.type == "text":
            message += MessageSegment.text(str(seg.data))
        elif seg.type == "image":
            file_id = await _v12_image(bot, seg.data)
            if file_id:
                message += MessageSegment.image(file_id)
            else:
                message += MessageSegment.text("[图片]")
        elif seg.type == "at":
            message += MessageSegment.mention(str(seg.data))
    if len(message) == 0:
        message += MessageSegment.text(out.plain_text or "（空消息）")
    return message


def _qq_build(out: OutMessage, at_user: str = "", user_type: str = "group") -> Any:
    from nonebot.adapters.qq import Message, MessageSegment

    message = Message()
    if at_user and user_type != "direct":
        try:
            message += MessageSegment.mention_user(at_user)
        except Exception:
            pass
    for seg in out.segments:
        if seg.type == "text":
            message += MessageSegment.text(str(seg.data))
        elif seg.type == "image":
            try:
                message += MessageSegment.file_image(bytes(seg.data), "pokemon.jpg")
            except Exception:
                message += MessageSegment.text("[图片]")
        elif seg.type == "at":
            try:
                message += MessageSegment.mention_user(str(seg.data))
            except Exception:
                pass
    if len(message) == 0:
        message += MessageSegment.text(out.plain_text or "（空消息）")
    return message


def _append_button_hint(out: OutMessage, kind: str) -> OutMessage:
    """非按钮平台把按钮数据转成纯文本提示，保证交互可用。"""

    if kind in {"web", "qq"} and out.buttons:
        # QQ 官方有键盘能力，但构造复杂；先给文本提示，后续可在 web 端扩展
        pass
    hint = out.text_and_button_hint()
    if hint:
        out.segments.append(Segment("text", hint))
    return out


async def send_message(
    bot: Any,
    nb_event: Any,
    out: OutMessage,
    *,
    at_sender: bool = False,
    kind: Optional[str] = None,
) -> SendResult:
    kind = kind or adapter_kind(bot, nb_event)
    result = SendResult.from_message(out)
    if kind == "web":
        return result

    if kind != "web" and out.buttons:
        out = _append_button_hint(out, kind)

    try:
        if kind == "onebot11":
            user_id = str(getattr(nb_event, "user_id", "") or "")
            message = _v11_build(out, user_id if at_sender else "")
            result.raw = await bot.send(nb_event, message)
        elif kind == "onebot12":
            user_id = str(getattr(nb_event, "user_id", "") or "")
            message = await _v12_build(bot, out, user_id if at_sender else "")
            result.raw = await bot.send(nb_event, message)
        elif kind == "qq":
            user_id = str(nb_event.get_user_id()) if hasattr(nb_event, "get_user_id") else ""
            user_type = "direct" if "C2C" in type(nb_event).__name__ else "group"
            message = _qq_build(out, user_id if at_sender else "", user_type)
            result.raw = await bot.send(nb_event, message)
        else:
            result.ok = False
            result.error = f"不支持的适配器: {type(nb_event).__module__}"
    except Exception as exc:
        logger.warning(f"[pokemon] 发送消息失败: {exc}")
        result.ok = False
        result.error = str(exc)
    return result


class ProactiveBot:
    """供 gss.active_bot 使用的主动推送包装。"""

    def __init__(self, bot: Any, kind: str):
        self.bot = bot
        self.kind = kind
        self.bot_id = str(getattr(bot, "self_id", "") or "")

    async def target_send(
        self,
        message: Any,
        target_type: str,
        target_id: Optional[str],
        bot_self_id: str = "",
        _unused: str = "",
        __unused: str = "",
        **kwargs: Any,
    ) -> Any:
        out = OutMessage.coerce(message)
        if not target_id:
            return None
        try:
            if self.kind == "onebot11":
                from nonebot.adapters.onebot.v11 import MessageSegment

                text = out.plain_text
                if target_type == "group":
                    return await self.bot.send_group_msg(group_id=int(target_id), message=MessageSegment.text(text))
                return await self.bot.send_private_msg(user_id=int(target_id), message=MessageSegment.text(text))
            if self.kind == "onebot12":
                return await self.bot.call_api(
                    "send_message",
                    detail_type="group" if target_type == "group" else "private",
                    group_id=target_id if target_type == "group" else None,
                    user_id=target_id if target_type != "group" else None,
                    message=out.plain_text,
                )
        except Exception as exc:
            logger.warning(f"[pokemon] 主动推送失败: {exc}")
        return None


def register_proactive(bot: Any, kind: Optional[str] = None) -> None:
    kind = kind or "onebot11"
    if kind == "unknown":
        return
    bot_id = str(getattr(bot, "self_id", "") or "")
    if bot_id:
        gss.active_bot[bot_id] = ProactiveBot(bot, kind)


__all__ = ["ProactiveBot", "SendResult", "register_proactive", "send_message"]
