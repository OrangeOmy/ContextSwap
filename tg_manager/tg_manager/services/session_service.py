"""
会话业务逻辑（步骤 3：先 stub Telegram）。

职责：
- 基于 transaction_id 进行幂等创建
- 查询会话（不存在则 404）
- 幂等结束会话
"""

from __future__ import annotations

import json
import sqlite3

from tg_manager.db.engine import utc_now_iso
from tg_manager.db.models import (
    AlreadyExistsError,
    Session,
    create_session,
    get_session_by_transaction_id,
    update_session_fields,
)
from tg_manager.services.telethon_service import TelethonService


class NotFoundError(RuntimeError):
    """资源不存在。"""


# 会话结束标记：seller 在最终消息中携带该标记，服务端会在完成最后一次转发后自动销毁会话
SESSION_END_MARKER = "[END_OF_REPORT]"
# 转发触发标记：buyer/seller 只有在段落末尾携带该标记，服务端才会转发当前累积内容
RELAY_FLUSH_MARKER = "[READY_TO_FORWARD]"


def create_session_idempotent(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    metadata_json: str,
) -> Session:
    """幂等创建会话：若已存在则直接返回已有记录。"""

    try:
        return create_session(conn, transaction_id=transaction_id, metadata_json=metadata_json)
    except AlreadyExistsError:
        got = get_session_by_transaction_id(conn, transaction_id)
        if got is None:
            raise RuntimeError("会话已存在但读取失败（不应发生）")
        return got


def get_session_or_404(conn: sqlite3.Connection, *, transaction_id: str) -> Session:
    got = get_session_by_transaction_id(conn, transaction_id)
    if got is None:
        raise NotFoundError(f"会话不存在：transaction_id={transaction_id}")
    return got


def end_session_idempotent(conn: sqlite3.Connection, *, transaction_id: str, reason: str) -> Session:
    """幂等结束：已结束则直接返回；未结束则写入结束字段。"""

    got = get_session_by_transaction_id(conn, transaction_id)
    if got is None:
        raise NotFoundError(f"会话不存在：transaction_id={transaction_id}")
    if got.status == "ended":
        return got

    return update_session_fields(
        conn,
        transaction_id=transaction_id,
        fields={
            "status": "ended",
            "session_end_at": utc_now_iso(),
            "end_reason": reason,
        },
    )


def _safe_load_metadata(metadata_json: str) -> dict:
    try:
        data = json.loads(metadata_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _build_topic_title(transaction_id: str) -> str:
    tx = (transaction_id or "").strip()
    if not tx:
        raise ValueError("transaction_id 不能为空")
    return f"tx:{tx}"


def _build_system_message(transaction_id: str, metadata: dict) -> str:
    # 兼容历史数据可能存了带 @ 的形式：这里统一剥离，避免出现 @@xxx
    buyer = str(metadata.get("buyer_bot_username") or "").strip().lstrip("@").strip()
    seller = str(metadata.get("seller_bot_username") or "").strip().lstrip("@").strip()
    prompt = metadata.get("initial_prompt")
    prompt_text = str(prompt).strip() if prompt is not None else ""
    if prompt_text == "":
        prompt_text = "（无）"
    market_slug = str(metadata.get("market_slug") or "").strip() or "will-donald-trump-win-the-2028-us-presidential-election"
    question_dir = str(metadata.get("question_dir") or "").strip() or "~/.openclaw/question"
    wait_seconds_raw = metadata.get("wait_seconds")
    wait_seconds = 120
    if isinstance(wait_seconds_raw, int) and wait_seconds_raw > 0:
        wait_seconds = wait_seconds_raw

    # 仅 @seller，避免 buyer bot 被系统注入消息误触发
    seller_mention = f"@{seller}" if seller else ""

    parts = [
        # 提前 @seller 提及，兼容 seller bot 开启隐私模式的场景
        seller_mention if seller_mention else "（未提供 seller bot 用户名，无法 @ 提及）",
        "",
        "交易会话已创建（Telegram Topic）",
        f"transaction_id: {transaction_id}",
    ]
    if buyer or seller:
        # buyer 仅展示用户名本体，不使用 @ 提及，避免触发 buyer bot 回复
        parts.append(f"参与方: {buyer or '未知'} / {seller_mention or seller or '未知'}")
    parts.extend(
        [
            "",
            "初始指令：",
            prompt_text,
            "",
            "Demo 上下文：",
            f"- market_slug: {market_slug}",
            f"- 异步答案目录: {question_dir}",
            f"- 主 bot 回收等待: {wait_seconds}s",
            "",
            "规则：",
            "- 请在本 Topic 内完成本次交易对话",
            f"- 你可以分多条消息组织一段内容；当这段内容准备好被转发时，请在最后一条末尾追加：{RELAY_FLUSH_MARKER}",
            f"- 服务端仅在检测到 {RELAY_FLUSH_MARKER} 后，才会把该 bot 自上次转发后的所有内容一次性转发给对方",
            f"- 子 topic bot 完成回答后，必须把完整回答保存为 md 到目录：{question_dir}",
            f"- 文件名格式：{transaction_id}__<bot_username>__answer.md",
            f"- 子 topic bot 在 Topic 回执中必须给出已写入文件名，并在末尾包含：{RELAY_FLUSH_MARKER}",
            f"- 主 bot 在发起委托后等待 {wait_seconds}s，再扫描 {question_dir} 并读取需要的 md 文件回填上下文",
            f"- 当 seller 输出最终报告后，请附带结束标记：{SESSION_END_MARKER}",
            f"- seller 的最终报告最后一段请同时包含：{SESSION_END_MARKER} 与 {RELAY_FLUSH_MARKER}",
            "- 服务端检测到结束标记后，会先把 seller 最后一条消息转发给 buyer，再自动关闭本 Topic",
        ]
    )
    return "\n".join(parts)


async def create_or_resume_session_with_telegram(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    incoming_metadata_json: str,
    market_chat_id: str,
    telegram: TelethonService,
    force_reinject: bool = False,
) -> Session:
    """创建或恢复会话（接入 Telegram Topic）。

幂等策略：
    - 若会话已存在且 message_thread_id 已就绪：直接返回
    - 若会话存在但 thread 缺失：尝试补齐 Telegram Topic，并更新会话字段
    - 若会话不存在：先写入 sessions（占位），再创建 Topic + 注入消息，最后更新会话为 running
    """

    tx = (transaction_id or "").strip()
    if not tx:
        raise ValueError("transaction_id 不能为空")
    chat_id = (market_chat_id or "").strip()
    if not chat_id:
        raise ValueError("market_chat_id 不能为空（MARKET_CHAT_ID）")

    got = get_session_by_transaction_id(conn, tx)
    if got is not None and got.chat_id and got.message_thread_id:
        if not force_reinject:
            return got
        if got.status == "ended":
            raise ValueError("会话已结束，不能重新注入系统消息（请使用新的 transaction_id）")

        # 允许在“会话已存在”的情况下强制重新注入，用于修复早期版本未包含 @ 提及的场景
        metadata = _safe_load_metadata(incoming_metadata_json)
        system_message = _build_system_message(tx, metadata)
        await telegram.send_message(
            chat_id=str(got.chat_id),
            message_thread_id=int(got.message_thread_id),
            text=system_message,
        )
        return got

    # 只在首次创建时写入 metadata；后续幂等请求不覆盖
    if got is None:
        got = create_session(conn, transaction_id=tx, status="created", metadata_json=incoming_metadata_json)

    metadata = _safe_load_metadata(got.metadata_json)
    title = _build_topic_title(tx)
    system_message = _build_system_message(tx, metadata)

    thread_id = got.message_thread_id
    if thread_id is None:
        thread_id = await telegram.create_topic(chat_id=chat_id, title=title)
        await telegram.send_message(chat_id=chat_id, message_thread_id=thread_id, text=system_message)

    return update_session_fields(
        conn,
        transaction_id=tx,
        fields={"chat_id": chat_id, "message_thread_id": int(thread_id), "status": "running"},
    )


async def end_session_with_telegram_cleanup(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    reason: str,
    telegram: TelethonService | None,
) -> Session:
    """结束会话并尝试关闭 Topic（若配置可用）。"""

    tx = (transaction_id or "").strip()
    if not tx:
        raise ValueError("transaction_id 不能为空")

    got = get_session_by_transaction_id(conn, tx)
    if got is None:
        raise NotFoundError(f"会话不存在：transaction_id={tx}")
    if got.status == "ended":
        return got

    if telegram is not None and got.chat_id and got.message_thread_id is not None:
        # 先清理 Topic；失败则不落库，便于重试
        await telegram.close_topic(chat_id=str(got.chat_id), message_thread_id=int(got.message_thread_id))

    return update_session_fields(
        conn,
        transaction_id=tx,
        fields={
            "status": "ended",
            "session_end_at": utc_now_iso(),
            "end_reason": reason,
        },
    )
