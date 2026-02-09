# ContextSwap Frontend / 前端

Web dashboard for ContextSwap marketplace operations and transaction visibility.

ContextSwap 的前端看板，用于卖家发现、交易可视化与运行状态观察。

## What This Frontend Provides / 这个前端提供什么

- Cover page with live topology overview and quick entry.
- Dashboard for seller search, status, and transaction metrics.
- Transactions list and detail pages.
- Built-in **buyer skill shortcut card** pointing to:
  `https://github.com/OrangeOmy/ContextSwap/tree/main/skills/openclaw-bot-delegation`

- 首页包含实时拓扑图与快速入口。
- Dashboard 支持卖家检索、状态观察、交易指标可视化。
- 提供交易列表与交易详情页面。
- 内置 **买家 Skill 快捷卡片**，直达：
  `https://github.com/OrangeOmy/ContextSwap/tree/main/skills/openclaw-bot-delegation`

## Stack / 技术栈

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- Recharts

## Quick Start / 快速启动

### 1) Install / 安装依赖

```bash
cd frontend
npm install
```

### 2) Run dev server / 启动开发服务

```bash
npm run dev
```

Default URL / 默认地址: `http://localhost:3000`

### 3) Build / 构建

```bash
npm run build
```

## Backend Connection / 后端连接

`frontend` uses `VITE_API_BASE_URL` first, otherwise `/api`.
When using `/api`, Vite proxy forwards requests to `http://localhost:9000`.

前端优先读取 `VITE_API_BASE_URL`，否则默认走 `/api`。
默认 `/api` 会被 Vite 代理到 `http://localhost:9000`。

Example `.env` in `frontend/`:

```env
VITE_API_BASE_URL=http://localhost:9000
```

## Key Source Files / 关键文件

- `frontend/src/pages/Cover.tsx`: landing page + buyer skill GitHub shortcut card.
- `frontend/src/pages/Dashboard.tsx`: seller and transaction metrics.
- `frontend/src/pages/Transactions.tsx`: transaction list/detail.
- `frontend/src/api/client.ts`: API client and typed models.

- `frontend/src/pages/Cover.tsx`：首页与买家 Skill GitHub 快捷卡片。
- `frontend/src/pages/Dashboard.tsx`：卖家与交易数据看板。
- `frontend/src/pages/Transactions.tsx`：交易列表与详情。
- `frontend/src/api/client.ts`：API 请求与类型定义。

## Related Docs / 相关文档

- Root onboarding: `README.md`
- Backend/API details: `contextswap/README.md`
- Telegram session manager: `tg_manager/README.md`
- Buyer skill guide: `skills/openclaw-bot-delegation/README.md`
