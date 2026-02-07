import os

import uvicorn

from contextswap.platform.api.app import build_app


def main() -> None:
    app = build_app()

    host = os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    port_raw = os.environ.get("PORT", "9000").strip() or "9000"
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"PORT must be int, got: {port_raw!r}") from exc

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
