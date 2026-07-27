# BackTranslate MVP 设计规格

## 一、项目概述

### 产品名称
BackTranslate（回译训练）

### 产品定位
针对影视字幕的**汉译英输出训练** AI 学习工具。

核心学习循环：**输出 → AI批改 → 理解差异 → 重新输出**

### 设计理念
1. **AI 不打断学习**：异步后台批改，翻译节奏不被 AI 响应速度中断
2. **AI 是老师，不是裁判**：帮助理解"为什么"，而非判对错
3. **官方字幕不是唯一答案**：评价表达质量，不逐字对比

---

## 二、技术栈

| 项目 | 选型 |
|------|------|
| 语言 | Python 3.11+ |
| GUI 框架 | PySide6 |
| 数据库 | SQLite |
| AI 接口 | OpenAI 兼容格式（Base URL / API Key / Model 用户可配） |
| 配置存储 | 明文 JSON 配置文件（含 API Key） |
| 网络 | 纯在线，无离线支持 |

---

## 三、窗口与导航

单窗口，左侧导航栏 + 右侧内容区，4 个页面：

| 导航项 | 页面名 | 功能 |
|--------|--------|------|
| 学习 | Learn | 导入 SRT + Sprint 翻译 |
| 复盘 | Review | 逐句查看 AI 点评与操作 |
| 表达库 | Expressions | 浏览/复习收藏的表达 |
| 设置 | Settings | API 配置 + Prompt 编辑 |

---

## 四、核心流程

### 4.1 Sprint 模式（MVP 唯一模式）

```
导入中英 SRT → 配对 → 从第1句开始翻译
    │
    ├─ 翻译界面：进度条 + "第 3/50 句" + 中文源句 + 输入框
    ├─ 用户输入英文 → Enter → 自动进入下一句
    ├─ 同时：该句翻译立即送入 AI 队列，后台异步批改
    │
    ├─ 用户主动点"结束学习" → 进入复盘
    ├─ 中途关闭窗口 → 进度不保存，重启回到学习首页
    │
    └─ 复盘：
         ├─ 列表总览（所有句子 + 评分摘要/批改状态）
         ├─ 未批改完的句子：显示"批改中…"，完成后动态出现
         ├─ 批改失败的句子：显示"批改失败，点击重试"
         └─ 点击某句 → 详情页：
              ├─ AI 多维评分（Meaning / Grammar / Naturalness / Subtitle Style）
              ├─ AI 分析文本
              ├─ 查看官方字幕（默认隐藏，点击展开）
              ├─ 自我评分 😊😐😓
              ├─ 重新翻译 → 生成新 version，AI 再批改，全部版本保留
              └─ 收藏表达（AI 推荐 ★★★★★ + 用户手动添加）
```

### 4.2 精读模式（Deep Study）
MVP 不做，留 v2。

---

## 五、数据模型

### 5.1 表结构

```sql
-- 会话（仅保留最近一次）
sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,                    -- 如 "Friends S01E01"
    created_at DATETIME,
    total_sentences INTEGER,
    completed_sentences INTEGER   -- 用户已翻译的句数
)

-- 字幕行（中英配对后）
subtitles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    index INTEGER,               -- 序号，从 1 开始
    chinese TEXT,                -- 中文原文
    english_official TEXT,       -- 官方英文字幕

    -- 上下文（简化版：前1 + 后1）
    prev_chinese TEXT,
    prev_english TEXT,
    next_chinese TEXT,
    next_english TEXT
)

-- 翻译记录（含 Redo，保留全部版本）
translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER REFERENCES subtitles(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,   -- 1=初译, 2/3...=Redo
    user_input TEXT,
    created_at DATETIME
)

-- AI 批改
evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id INTEGER REFERENCES translations(id) ON DELETE CASCADE,
    meaning_score INTEGER,        -- 0-100
    grammar_score INTEGER,        -- 0-100
    naturalness_score INTEGER,    -- 0-100
    subtitle_style_score INTEGER, -- 0-100
    analysis_text TEXT,           -- AI 分析全文
    suggested_expressions TEXT,   -- AI 建议收藏的表达，JSON array
    status TEXT DEFAULT 'pending', -- pending/processing/done/failed
    error_message TEXT,
    created_at DATETIME
)

-- 表达收藏（独立持久化，不受 session 覆盖影响）
expressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT,                  -- 收藏的表达
    source_subtitle_id INTEGER,   -- 来源字幕（可为空）
    collected_at DATETIME,
    notes TEXT                    -- 用户备注
)

-- 自我评分
self_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER UNIQUE REFERENCES subtitles(id) ON DELETE CASCADE,
    rating INTEGER,               -- 1=😓, 2=😐, 3=😊
    created_at DATETIME
)
```

### 5.2 数据生命周期

- **新建 session**：DELETE 旧 session，级联删除 subtitles / translations / evaluations / self_ratings
- **expressions**：独立于 session，永久保留，除非用户手动删除

---

## 六、SRT 导入与配对

### 6.1 导入
- 用户分别选择中文 SRT 文件和英文 SRT 文件
- 支持两种配对策略，用户选择：
  - **按时间轴匹配**：同一时间段的中英文字幕自动配对
  - **按序号匹配**：逐行对应（第1句中配第1句英）

### 6.2 配对后
- 自动计算上下文（prev / next 各 1 句）
- 构建 subtitles 表记录
- 配对成功后直接进入翻译界面，从第 1 句开始，无预设句数上限

---

## 七、AI 集成

### 7.1 接口格式
OpenAI 兼容的 Chat Completions API：
```
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Body: { "model": "{model}", "messages": [...] }
```

### 7.2 API 配置
Settings 页提供三个字段：
- Base URL（默认：`https://api.deepseek.com`）
- API Key
- Model（默认：`deepseek-chat`）

### 7.3 Prompt 管理
- Settings 页提供可编辑的 Prompt 模板输入框
- 内置默认 Prompt（符合设计文档中的批改原则）
- 模板变量：`{context}`（上下文）、`{user_input}`（用户翻译）、`{official}`（官方字幕）

### 7.4 AI 调用时机
- 用户每提交一句翻译，**立即**触发一次 AI 批改调用
- 后台异步，不阻塞用户继续翻译

### 7.5 AI 上下文
- 发送：前 N 句 + 当前句 + 后 N 句（N 在设置页可调，默认 1）
- 提供中文原文 + 官方英文 + 用户英文

### 7.6 输出要求
AI 返回结构化 JSON：
```json
{
  "meaning_score": 95,
  "grammar_score": 100,
  "naturalness_score": 82,
  "subtitle_style_score": 75,
  "analysis": "全文分析...",
  "suggested_expressions": ["figure out", "I couldn't agree more"]
}
```

### 7.7 错误处理
- 失败自动重试 3 次（间隔递增）
- 3 次仍失败：标记为 `failed`，复盘页显示"批改失败，点击重试"

---

## 八、复盘页交互

### 8.1 列表视图
- 所有句子纵向排列
- 每句显示：序号、中文原文缩略、评分总览（已批改）/ 状态标记（进行中/失败）
- 已完成的句子按评分用不同颜色标记（绿色高分 / 黄色中等 / 红色需改进）

### 8.2 详情面板（点击某句展开）
- AI 四维评分（数值 + 进度条/星级可视化）
- AI 分析文字
- **官方字幕**：默认折叠，点击展开
- **自我评分**：😊😐😓 三选一
- **重新翻译**：输入框 + 提交按钮 → 生成新 version → 触发 AI 再批改
- **收藏表达**：AI 标记的推荐表达 + 手动添加按钮

---

## 九、表达库

- 持久化存储，独立于 session
- 列表展示所有已收藏表达
- 支持搜索/筛选
- 点击可查看来源句子上下文

---

## 十、设置页

| 设置项 | 说明 |
|--------|------|
| Base URL | AI API 地址 |
| API Key | 鉴权密钥 |
| Model | 模型名称 |
| 上下文字数 | 发送给 AI 的前后句数量（N，默认 1，范围 0-5） |
| Prompt 模板 | 可编辑的 AI Prompt |
| 保存/重置按钮 | 保存配置 / 恢复默认 Prompt |

---

## 十一、MVP 范围清单

| 功能 | MVP |
|------|-----|
| SRT 导入（中英独立文件） | ✅ |
| 时间轴/序号两种配对 | ✅ |
| Sprint 连续翻译 | ✅ |
| AI 后台异步批改 | ✅ |
| 集中复盘（列表 + 详情） | ✅ |
| 官方字幕对比（默认隐藏） | ✅ |
| 重新翻译（保留全部版本） | ✅ |
| 四维评分 | ✅ |
| 表达收藏（AI 推荐 + 手动） | ✅ |
| 上下文可调（默认 ±1，范围 0-5） | ✅ |
| API 配置 + Prompt 编辑 | ✅ |
| 自我评分（复盘时） | ✅ |
| 动态进入复盘（完成一句出现一句） | ✅ |
| AI 失败自动重试 + 手动重试 | ✅ |
| 深读模式（Deep Study） | ❌ v2 |
| 上下文 ±2 句 | ❌ v2 |
| Hint 关键词提示 | ❌ v2 |
| 长期学习统计 | ❌ v2 |
| 会话历史 | ❌ v2 |
| 离线翻译 | ❌ 不做 |

---

## 十二、后续扩展（v2+）

- Deep Study 模式（逐句即时反馈）
- Hint 关键词提示
- 长期学习统计（错误趋势）
- 会话历史保留与复习
- 多 AI Provider 切换 UI
