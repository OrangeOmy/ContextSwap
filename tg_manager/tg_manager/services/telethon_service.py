"""
Telethon 服务封装（MTProto userbot）。

设计目标：
- 使用“用户账号”身份在超级群 Topic 内发言/管理话题
- 能读取并处理 bot 发出的消息（Bot API 做不到）
- 快速反应：授权/参数异常直接抛出明确错误

重要说明：
- 本项目使用方案 B（超级群 + Forum Topics），每个交易创建一个 Topic。
- Telegram Bot API 的 message_thread_id 在 Topic 场景里本质上是“线程标识”，与 MTProto 的 forum topic 顶层消息/线程 id 对齐；
  我们在实现中以“Topic 顶层消息 id（top message id）”作为 message_thread_id 持久化与路由依据。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from telethon import TelegramClient
from telethon.tl import functions


class TelethonError(RuntimeError):
    """Telethon 调用失败。"""


def _ensure_topic_title(title: str) -> str:
    t = (title or "").strip()
    if not t:
        raise ValueError("Topic 标题不能为空")
    # Telegram ForumTopic 名称上限 128
    if len(t) > 128:
        t = t[:128]
    return t


def _extract_thread_id_from_updates(result: Any) -> int:
    """
    从 CreateForumTopic 的返回 updates 中提取 topic 的顶层消息 id（作为 message_thread_id）。

    Telethon 返回通常是 Updates/UpdatesCombined 一类，包含 updates 列表。
    我们采用“鸭子类型”提取：找到 update.message.id 即认为是顶层消息 id。
    """

    updates = getattr(result, "updates", None)
    if not isinstance(updates, list):
        raise TelethonError(f"无法从返回中解析 updates：{type(result).__name__}")

    for upd in updates:
        msg = getattr(upd, "message", None)
        mid = getattr(msg, "id", None)
        if isinstance(mid, int) and mid > 0:
            return mid

    raise TelethonError("无法从 CreateForumTopic 返回中提取 message_thread_id（未找到 update.message.id）")


@dataclass(frozen=True)
class TelethonService:
    client: TelegramClient

    async def create_topic(self, *, chat_id: str, title: str) -> int:
        """创建 Forum Topic 并返回 message_thread_id（顶层消息 id）。"""

        name = _ensure_topic_title(title)
        try:
            peer = await self.client.get_input_entity(int(str(chat_id).strip()))
            result = await self.client(functions.messages.CreateForumTopicRequest(peer=peer, title=name))
        except Exception as exc:  # Telethon 异常类型较多，MVP 先统一封装
            raise TelethonError(f"创建 Topic 失败：{exc}") from exc
        return _extract_thread_id_from_updates(result)

    async def send_message(self, *, chat_id: str, message_thread_id: int, text: str) -> int:
        """在指定 Topic 内发送消息，返回 message_id（用于排障）。"""

        t = (text or "").strip()
        if not t:
            raise ValueError("发送消息内容不能为空")

        try:
            peer = await self.client.get_input_entity(int(str(chat_id).strip()))
            msg = await self.client.send_message(peer, t, reply_to=int(message_thread_id))
        except Exception as exc:
            raise TelethonError(f"发送消息失败：{exc}") from exc

        mid = getattr(msg, "id", None)
        return int(mid) if isinstance(mid, int) else 0

    async def close_topic(self, *, chat_id: str, message_thread_id: int) -> None:
        """关闭 Forum Topic（最小清理）。"""

        try:
            peer = await self.client.get_input_entity(int(str(chat_id).strip()))
            await self.client(
                functions.messages.EditForumTopicRequest(
                    peer=peer,
                    topic_id=int(message_thread_id),
                    closed=True,
                )
            )
        except Exception as exc:
            raise TelethonError(f"关闭 Topic 失败：{exc}") from exc
