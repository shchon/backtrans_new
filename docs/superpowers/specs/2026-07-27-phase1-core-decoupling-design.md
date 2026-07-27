# Phase 1: Python 核心解耦 — 设计文档

## 概述

将现有 PySide6 代码重构为清晰的层次架构：Models (dataclass) → Services → Database/AI/Config。UI 页面不再直接访问数据库操作，Worker 不再包含业务逻辑，所有数据用 dataclass 表示。

## 背景

当前应用 BackTranslate（回译训练）是一个 PySide6 桌面应用，主要问题：
- UI 页面直接 import `database/operations.py` 调用 CRUD
- 业务逻辑散落在 `main.py` 的 App 编排器中
- AI Worker 既负责队列又负责数据库写入
- 所有数据以原始字典形式传递，无类型约束

## 架构

```
┌─────────────────────────────────────────────────┐
│  UI Pages (learn_page.py, review_page.py, ...)  │
│    只通过 Service 访问数据，不直接操作 DB         │
├─────────────────────────────────────────────────┤
│  Services Layer (按领域拆分)                     │
│  SessionService / SubtitleService / ...          │
│  封装所有业务逻辑，接收/返回 dataclass            │
├──────────────────┬──────────────────────────────┤
│  Models(dataclass)│  database/ + ai/ + config/  │
│  SubtitleLine    │  (纯数据访问, 被 Services    │
│  Session         │   调用, 不暴露给 UI)          │
│  Evaluation      │                               │
└──────────────────┴──────────────────────────────┘
```

## Models（dataclass，标准库）

所有 dataclass 放在 `backtranslate/models/` 包中：

| 模型 | 所在文件 | 关键字段 |
|------|---------|---------|
| `SubtitleLine` | subtitle.py | idx, chinese, english_official, prev_*, next_* |
| `Session` | session.py | id, name, total_sentences, completed_sentences, created_at |
| `SubtitlePair` | subtitle.py | index, chinese_text, english_text, start_ms, end_ms |
| `Translation` | translation.py | id, subtitle_id, version, user_input, created_at |
| `Evaluation` | translation.py | id, translation_id, *score, analysis_text, suggested_expressions |
| `Expression` | expression.py | id, phrase, source_subtitle_id, notes |
| `SelfRating` | translation.py | subtitle_id, rating |
| `AppSettings` | config.py | base_url, api_key, model, context_n, font_size, ... |
| `LearningStats` | stats.py | date, sentence_count, session_count |
| `StreakEntry` | stats.py | date, sentences_completed |

## Services（按领域拆分）

放在 `backtranslate/services/` 包中。每个 Service 类通过构造器接收 `get_connection: Callable[[], sqlite3.Connection]` 依赖。

| Service | 文件 | 主要方法 |
|---------|------|---------|
| `SessionService` | session_service.py | create, get_current, update_progress, delete_old |
| `SubtitleService` | subtitle_service.py | get_by_session, get_by_id, save_batch, delete_by_session |
| `TranslationService` | translation_service.py | create, get_by_subtitle, get_versions |
| `EvaluationService` | evaluation_service.py | save, get_by_subtitle, get_all_for_session |
| `ExpressionService` | expression_service.py | add, search, delete, list_all |
| `ConfigService` | config_service.py | load, save, get, update |
| `SrtService` | srt_service.py | parse_file, pair_subtitles, import_pair |
| `AiService` | ai_service.py | evaluate_translation, build_context, test_connection |
| `FavoriteService` | favorite_service.py | add, remove, is_favorited, list_all |
| `SelfRatingService` | self_rating_service.py | save, get_by_subtitle |
| `StatsService` | stats_service.py | record_daily, get_streak, get_today_count |

## Worker 精简

`backtranslate/ai/worker.py`：
- 只维护任务队列 + QThread 轮询
- 调用 `AiService` 获取 AI 响应
- 通过信号返回结果：`evaluation_done(int, dict)` / `evaluation_failed(int, str)`
- 不再直接操作数据库

## UI 页面改造

每个页面通过构造器注入所需的 Service：

```
LearnPage(session_service, subtitle_service, translation_service,
          ai_service, config_service, srt_service, stats_service, parent)
ReviewPage(evaluation_service, expression_service,
           translation_service, subtitle_service, favorite_service,
           self_rating_service, config_service, parent)
FavoritesPage(subtitle_service, favorite_service, parent)
ExpressionsPage(expression_service, parent)
SettingsPage(config_service, parent)
```

删除所有页面中直接 `from backtranslate.database.operations import ...` 的导入。

## main.py 简化

App 类职责减少为：
1. 创建所有 Service 实例（共享 `get_connection`）
2. 创建 Pages 并注入 Service
3. 信号连接（页面信号 → Service 方法）
4. 启动 Worker 线程

## 不涉及的范围（保持原样）

- SRT parser.py / pairing.py — 仅通过 SrtService 访问
- AI client.py — 仅通过 AiService 访问
- config.py / _paths.py / defaults.py — 仅通过 ConfigService 访问
- SQLite schema — 保持现有 DDL
- 测试 — 现有测试继续通过（新代码加新测试）

## 测试策略

- Models：测试 dataclass 创建和序列化（简单，可选）
- Services：为每个 Service 写 pytest 测试，使用内存 SQLite
- UI 页面：保持现有状态，不做大改动
- 集成测试：确保重构后功能与之前一致
