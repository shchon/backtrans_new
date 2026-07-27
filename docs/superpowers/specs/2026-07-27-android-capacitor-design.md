# Android/Capacitor 纯前端移植 — 设计文档

## 概述

将 React 前端从依赖 FastAPI 后端改为纯前端架构，数据库用 sql.js 在浏览器中操作 SQLite，AI 调用直接从前端发出，然后用 Capacitor 打包为 Android 应用。

## 架构

```
React Frontend (浏览器/WebView)
├── sql.js (SQLite WASM) — 直接操作 data/backtranslate.db
├── fetch() — 直接调 OpenAI 兼容 API
├── SRT parser (TypeScript) — 解析 .srt 文件
└── localStorage — 存储配置
```

## 目录结构

```
frontend/src/
├── db/                          # 新增：数据库层
│   ├── index.ts                 # 初始化 sql.js + 连接管理
│   ├── schema.ts                # DDL (复用现有 SQLite schema)
│   └── operations.ts            # CRUD 函数 (移植自 operations.py)
├── ai/
│   └── client.ts                # 新增：直接 fetch 调 AI API
├── srt/
│   ├── parser.ts                # 新增：移植自 Python parser.py
│   └── pairing.ts               # 新增：移植自 Python pairing.py
├── config/
│   └── index.ts                 # 新增：localStorage 配置管理
├── api/
│   └── client.ts                # 改为可选：开发模式走 API，生产直接调本地 DB
├── pages/                       # 5 个页面 (已有，需改为直接操作 db/)
│   ├── LearnPage.tsx             # 改为使用 db/operations.ts
│   ├── ReviewPage.tsx
│   ├── FavoritesPage.tsx
│   ├── ExpressionsPage.tsx
│   └── SettingsPage.tsx
└── App.tsx
```

## 数据库移植

用 sql.js 替代 Python sqlite3，数据库 schema 完全相同。

```typescript
// db/index.ts — 初始化
import initSqlJs, { Database as SqlJsDatabase } from 'sql.js';

let db: SqlJsDatabase;

export async function initDatabase(): Promise<void> {
  const SQL = await initSqlJs({ locateFile: file => `https://sql.js.org/dist/${file}` });
  db = new SQL.Database();
  createTables(db);
}

export function getDb(): SqlJsDatabase { return db; }
```

每个 operations 函数从 Python 映射到 TypeScript：

```typescript
// Python: def create_session(name, total_sentences): ...
// TypeScript:
export function createSession(name: string, totalSentences: number): number {
  const db = getDb();
  db.run("INSERT INTO sessions (name, total_sentences) VALUES (?, ?)", [name, totalSentences]);
  return Number(db.exec("SELECT last_insert_rowid()")[0].values[0][0]);
}
```

## AI 客户端

```typescript
// ai/client.ts
export async function callAi(
  baseUrl: string, apiKey: string, model: string,
  promptTemplate: string, context: string, userInput: string, official: string
): Promise<AiResult | null> {
  const prompt = promptTemplate.replace('{context}', context)
    .replace('{user_input}', userInput).replace('{official}', official);
  
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], temperature: 0.3 }),
  });
  // ... parse response
}
```

## Capacitor 集成

1. `npm install @capacitor/core @capacitor/cli @capacitor/android`
2. `npx cap init backtranslate com.backtranslate.app`
3. `npx cap add android`
4. 构建前端 → `npx cap copy` → `npx cap open android`
5. Android Studio 中构建 APK

## 不涉及

- Tauri 桌面壳（已有 FastAPI 模式可用）
- Python 后端的修改
- 数据库 schema 变更

## 移植范围（按优先级）

1. P0: sql.js 数据库层 + SRT 解析 + AI 客户端
2. P1: 页面改直接调用 db/operations
3. P2: Capacitor Android 打包
