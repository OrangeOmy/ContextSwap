"""
导出 Telethon StringSession（交互式）。

用途：
- 你需要先在本地完成一次验证码/2FA 登录，生成 TELETHON_SESSION，服务端才能无交互启动。

用法：
    set -a && source .env && set +a
    uv run python scripts/export_telethon_session.py
"""

from __future__ import annotations

import os

from telethon import TelegramClient
from telethon.sessions import StringSession


def _读取必填(key: str) -> str:
    v = (os.environ.get(key) or "").strip()
    if not v:
        raise ValueError(f"缺少必填环境变量：{key}")
    return v


async def main() -> None:
    api_id_raw = _读取必填("TELETHON_API_ID")
    try:
        api_id = int(api_id_raw)
    except ValueError as exc:
        raise ValueError(
            f"环境变量 TELETHON_API_ID 必须是整数，当前值：{api_id_raw!r}"
        ) from exc
    api_hash = _读取必填("TELETHON_API_HASH")

    print("请输入用于登录的手机号（带国家码，例如 +86xxxxxxxxxxx）：")
    phone = input("> ").strip()
    if not phone:
        raise ValueError("手机号不能为空")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        await client.send_code_request(phone)
        print("请输入 Telegram 发来的验证码：")
        code = input("> ").strip()
        if not code:
            raise ValueError("验证码不能为空")

        try:
            await client.sign_in(phone=phone, code=code)
        except Exception:
            # 可能触发 2FA 密码
            print("如账号开启了 2FA，请输入密码（不会回显）：")
            password = input("> ").strip()
            if not password:
                raise
            await client.sign_in(password=password)

        session_str = client.session.save()
        print("\n已生成 TELETHON_SESSION（请妥善保管，不要提交到 git）：\n")
        print(session_str)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
