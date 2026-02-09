# Database (`db/`)

SQLite storage directory for ContextSwap runtime data.

ContextSwap 运行时 SQLite 数据目录。

## Purpose / 作用

- Default DB file path: `./db/contextswap.sqlite3`
- Stores seller, transaction, and session data used by platform/tg_manager.

- 默认数据库路径：`./db/contextswap.sqlite3`
- 存储平台与 tg_manager 使用的卖家、交易、会话数据。

## Quick Inspect / 快速查看

```bash
sqlite3 ./db/contextswap.sqlite3 ".tables"
```

```bash
sqlite3 ./db/contextswap.sqlite3 "SELECT COUNT(*) FROM sellers;"
sqlite3 ./db/contextswap.sqlite3 "SELECT COUNT(*) FROM transactions;"
sqlite3 ./db/contextswap.sqlite3 "SELECT COUNT(*) FROM sessions;"
```

## Notes / 说明

- This folder is runtime data, not migration source.
- For API/schema details, see `contextswap/README.md` and `tg_manager/README.md`.

- 该目录属于运行时数据目录，不是迁移脚本目录。
- API 与 schema 细节见 `contextswap/README.md` 与 `tg_manager/README.md`。
