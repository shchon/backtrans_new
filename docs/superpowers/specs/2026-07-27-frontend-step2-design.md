# Step 2: 搭建新前端 (FastAPI + React) — 设计文档

## 概述

在 Phase 1 核心解耦的基础上，搭建 FastAPI 后端和 React 前端。实现最基本的页面（字幕列表），为后续 AI 集成做准备。

## 架构

```
React (Vite + TypeScript) ──HTTP──> FastAPI ──> backtranslate/services/ ──> data/backtranslate.db
```

- FastAPI 后端直接复用 Phase 1 的 `backtranslate/services/` 层
- 数据库路径沿用现有 `data/backtranslate.db`
- 前端用 Vite + React + TypeScript，通过 fetch 调用 API

## 目录结构

```
i:\python\backtranslatess\
├── backend/                        # FastAPI 后端
│   ├── main.py                     # uvicorn 入口
│   ├── api.py                      # REST 路由
│   └── schemas.py                  # Pydantic 请求/响应模型
├── frontend/                       # Vite + React + TypeScript
│   ├── src/
│   │   ├── App.tsx                 # 主应用
│   │   ├── App.css
│   │   ├── main.tsx                # 入口
│   │   ├── types.ts                # TypeScript 接口定义
│   │   ├── api/
│   │   │   └── client.ts           # API 调用封装
│   │   └── pages/
│   │       └── LearnPage.tsx       # 字幕列表页面（第一个页面）
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
```

## API 设计（第 2 步）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 列出所有学习会话 |
| GET | `/api/sessions/{id}/subtitles` | 获取会话的字幕列表 |
| GET | `/api/stats` | 获取学习统计 |

响应格式统一：
```json
{
  "sessions": [
    {"id": 1, "name": "会话名", "total_sentences": 100, "completed_sentences": 50, "created_at": "2024-01-01"}
  ]
}
```

```json
{
  "subtitles": [
    {"id": 1, "idx": 1, "chinese": "你好", "english_official": "Hello"}
  ]
}
```

## 前端页面

**LearnPage.tsx** — 简单明了的字幕列表：
- 顶部：标题 + 会话选择下拉框
- 主体：字幕列表（序号 | 中文 | 英文）
- 从当前数据库加载现有数据

**样式**：纯 CSS，保持简洁，接近现有桌面应用的风格。

## 暂不包含

- 用户认证
- Tauri 桌面壳（等 Rust 环境）
- AI 调用（Step 3）
- 翻译输入/提交功能（Step 3）
- 路由系统（单页足够）

## 启动方式

```bash
# 终端 1：后端
cd i:\python\backtranslatess
python -m uvicorn backend.main:app --port 8765 --reload

# 终端 2：前端
cd i:\python\backtranslatess\frontend
npm install
npm run dev
```
