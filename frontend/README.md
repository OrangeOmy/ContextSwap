# ContextSwap Dashboard

Web3风格的ContextSwap平台前端Dashboard。

## 技术栈

- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **React Router** - 路由管理
- **Axios** - HTTP客户端
- **Lucide React** - 图标库

## 特性

- 🎨 Web3风格UI设计（深色主题、霓虹色、科技感）
- 📊 实时数据统计看板
- 🔍 卖家搜索功能
- 💳 交易列表展示
- ⚡ 响应式设计
- 🎭 流畅的动画效果

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 环境变量

创建 `.env` 文件（可选）：

```env
VITE_API_BASE_URL=http://localhost:9000
```

默认情况下，开发服务器会通过Vite代理将 `/api` 请求转发到 `http://localhost:9000`。

## API集成

Dashboard集成了以下ContextSwap平台API：

- `GET /v1/sellers/search` - 搜索卖家
- `POST /v1/sellers/register` - 注册卖家
- `POST /v1/sellers/unregister` - 注销卖家
- `GET /v1/transactions/{transaction_id}` - 获取交易详情

## 设计风格

- **主色调**: 紫色 (#8b5cf6)、青色 (#06b6d4)、粉色 (#ec4899)
- **背景**: 深色 (#0a0a0f)
- **特效**: 发光效果、渐变、网格背景
- **动画**: 悬停效果、脉冲动画、浮动效果
