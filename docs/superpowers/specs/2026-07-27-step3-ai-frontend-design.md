# Step 3: AI 接入 + 完整前端页面 — 设计文档

## 概述

在 Step 2 基础上接入 AI 调用，完成全部 5 个前端页面（学习、复盘、收藏夹、表达库、设置），实现完整的回译训练流程。

## 架构

```
React Frontend ──REST──> FastAPI Backend ──> backtranslate/services/
                                                  │
                                            AI Client (call_ai)
                                                  │
                                          OpenAI-compatible API
```

- AI 调用异步执行：提交翻译 → 后端创建 evaluation → 后台线程调 AI → 更新状态 → 前端轮询结果
- 前端用 state 切换 5 个页面，不需要路由库

## API 端点（完整列表）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sessions | 会话列表 |
| GET | /api/sessions/{id}/subtitles | 字幕列表 |
| **POST** | **/api/sessions/import** | **导入 SRT 创建会话** |
| **POST** | **/api/sessions/{id}/translate** | **提交翻译 + 触发 AI** |
| **GET** | **/api/evaluations/{id}** | **轮询 AI 结果** |
| **GET** | **/api/sessions/{id}/evaluations** | **会话全部评估** |
| **POST** | **/api/evaluations/{id}/retry** | **重试失败评估** |
| **GET** | /api/stats | 学习统计 |
| **GET** | **/api/config** | **读取 AI 配置** |
| **PUT** | **/api/config** | **保存 AI 配置** |
| **GET** | **/api/expressions** | **表达库列表** |
| **POST** | **/api/expressions** | **添加表达** |
| **DELETE** | **/api/expressions/{id}** | **删除表达** |
| **GET** | **/api/favorites** | **收藏列表** |
| **POST** | **/api/favorites/{subtitle_id}** | **添加收藏** |
| **DELETE** | **/api/favorites/{subtitle_id}** | **取消收藏** |
| **POST** | **/api/sessions/{id}/complete** | **结束会话** |

（**粗体** = Step 3 新增）

## AI 异步流程

```
1. POST /translate → 后端创建 translation + evaluation(status=pending)
                     → 启动后台线程调用 AI API
                     → 立即返回 {eval_id, status: "pending"}
2. 前端每秒 GET /evaluations/{id} 轮询
3. AI 完成后 → 后端更新 evaluation(status=done, 分数, 分析)
4. 前端轮询到 status=done → 显示结果
5. 30 秒超时 → 显示"批改超时，可重试"
```

后台线程执行 AI 调用，直接复用 `backtranslate/ai/client.call_ai()`。

## 前端页面

### LearnPage（翻译 Sprint）
- 导入按钮 → 上传中英 SRT 文件弹窗 → 配对策略选择
- Sprint 模式：显示中文句子 → 输入框输入英文 → Enter/下一句提交
- 顶部进度条 + 进度文字
- 底部统计栏：连续天数、今日句数、总计
- 跳转输入框、跳过按钮
- 完成所有句子后弹出小结，自动跳转到复盘

### ReviewPage（评估列表）
- 显示当前会话的所有字幕，每行一个卡片
- 卡片左侧：序号 + 中文 + 评分摘要（综合分带颜色）
- 收藏星标按钮
- 展开后：AI 四维分数、AI 分析、官方字幕、重新翻译输入框、版本历史、收藏表达

### FavoritesPage（收藏夹）
- 列表显示收藏的字幕（中文 + 英文切换显示）
- 删除按钮
- 清空全部
- "复习收藏"按钮 → 创建新会话跳转到学习

### ExpressionsPage（表达库）
- 搜索过滤
- 列表显示收藏的表达
- 删除按钮

### SettingsPage（设置）
- Base URL / API Key / Model 输入
- 上下文句数设置
- 复盘字体大小
- Prompt 模板编辑器
- 保存按钮
- 测试连接按钮

### 导航
左侧边栏 5 个按钮，state 切换页面内容。

## 前端状态管理

- 每个页面自己管理自己的 state（useState + useEffect）
- 不需要全局状态管理
- API 调用统一走 `api/client.ts`
- 轮询用 `setInterval` + `useEffect` cleanup

## 暂不包含

- Tauri 桌面壳（等 Rust 环境）
- SRT 文件拖拽上传（用标准 file input）
