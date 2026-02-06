"""
服务启动入口。

运行方式：
    uv run main.py
"""

from __future__ import annotations

import os

import uvicorn

from tg_manager.api.app import build_app


def main() -> None:
    app = build_app()

    host = os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    port_raw = os.environ.get("PORT", "8000").strip() or "8000"
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 PORT 必须是整数，当前值：{port_raw!r}") from exc

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

