---
name: learning-upgrade
version: 3.0.0
description: 多源技术学习系统 v3 - 日/周/月三级复盘体系 - GitHub/社区监控 + 深度分析 + 行动项追踪 + Notion 日记/周报/月报
author: OpenClaw Agent
category: automation
requires:
  env:
    - GITHUB_TOKEN
    - MATON_API_KEY
    - ARK_API_KEY
  network:
    - api.github.com
    - gateway.maton.ai
    - news.ycombinator.com
    - ark.cn-beijing.volces.com
---

# Learning Upgrade 技能 v3.0

**日/周/月三级复盘体系** — 从被动记录升级为主动知识管理与成长追踪

---

## 📊 系统概述

```
┌──────────────────────────────────────────────────────┐
│                  三级复盘体系                          │
├──────────┬──────────────┬───────────────────────────────┤
│  📅 每日  │  📊 每周      │  📈 每月                      │
│  15:00   │  周一 09:00   │  1 日 10:00                   │
│          │              │                               │
│  信息收集  │  趋势聚合     │  成长分析                      │
│  深度分析  │  完成检查     │  知识盲区                      │
│  改进计划  │  改进列表     │  下月规划                      │
│  Notion   │  Notion 周报  │  Notion 月报                  │
│  Telegram │  Telegram    │  Telegram                    │
└──────────┴──────────────┴───────────────────────────────┘
```

---

## 🔄 三级流程详解

### 📅 每日 Pipeline（15:00 自动执行）

```
→ 环境验证 → GitHub 监控 → 社区抓取 → 技术深度分析 → Notion 日记 → Telegram ←
```

| 步骤 | 脚本 | 输出 |
|------|------|------|
| 1. GitHub 监控 | `github-monitor.py` | `logs/github-monitor/YYYYMMDD.md` |
| 2. 社区抓取 | `community-scraper.py` | `logs/community-scraper/YYYYMMDD.md` |
| 3. 技术分析 | `tech-analyzer.py` | `logs/tech-analyzer/YYYYMMDD.md` |
| 4. Notion 更新 | `notion-updater.py` | Notion 每日页面 |

**v3.0 增强**:
- 技术分析新增行动项输出 → 自动写入 `tracker/action-items.json`
- 生成日报汇总 → `logs/daily-digest/YYYYMMDD.md`

---

### 📊 每周 Pipeline（每周一 09:00 触发）

复盘上一周（周一~周日）全部内容，检查重点和完成情况。

| 步骤 | 说明 |
|------|------|
| 1. 加载日报 | 读取上周 7 份日报 (允许缺失) |
| 2. 聚合分析 | 技术热度 TOP5 / 关键事件 / 新知识 / 趋势对比 |
| 3. 完成检查 | 读取 action-items.json，统计完成率 |
| 4. 改进列表 | LLM 生成 5 项高价值改进建议 (含步骤+预期收益) |
| 5. Notion 周报 | 在月份页面下创建周报页面 |
| 6. Telegram 推送 | 推送精简周报摘要 |

**输出**: `logs/weekly-review/YYYY-Wxx.md` + Notion 周报页面

**核心脚本**: `weekly-reviewer.py` / `learning-weekly.sh`

---

### 📈 每月 Pipeline（每月 1 日 10:00 触发）

复盘上月所有周的情况，给出全面的成长分析和下月规划。

| 步骤 | 说明 |
|------|------|
| 1. 加载周报 | 读取上月全部周报 |
| 2. 趋势分析 | 技术演进路径 / 学习投入 / 信息源质量 |
| 3. 知识图谱 | 覆盖分析 / 深度vs广度 / 盲区识别 |
| 4. 下月规划 | LLM 生成重点方向 + 推荐资源 + 月度挑战 |
| 5. Notion 月报 | 在根页面下创建月度复盘页面 |
| 6. Telegram 推送 | 推送月度复盘摘要 |

**输出**: `logs/monthly-review/YYYY-MM.md` + Notion 月度复盘页面

**核心脚本**: `monthly-reviewer.py` / `learning-monthly.sh`

---

## 🛠️ 文件清单

| 脚本 | 状态 | 功能 |
|------|------|------|
| `tools/github-monitor.py` | 不变 | GitHub 动态监控 |
| `tools/community-scraper.py` | 不变 | 社区趋势抓取 |
| `tools/verify-env.sh` | 不变 | 环境变量验证 |
| `tools/tech-analyzer.py` | **修改** | 增加行动项输出 |
| `tools/notion-updater.py` | **修改** | 支持日/周/月三种页面创建 |
| `tools/action-tracker.py` | **新增** | 行动项追踪管理 |
| `tools/weekly-reviewer.py` | **新增** | 每周复盘分析 |
| `tools/monthly-reviewer.py` | **新增** | 每月复盘分析 |
| `tools/learning-daily.sh` | **修改** | 增加行动项写入步骤 |
| `tools/learning-weekly.sh` | **新增** | 周报编排入口 |
| `tools/learning-monthly.sh` | **新增** | 月报编排入口 |

---

## 📝 Notion 页面结构

```
学习日记（claw）[根页面]
│
├─ 📅 2026 年 2 月学习日记             [月份页面]
│   ├─ 2026-02-17 学习日报             [每日]
│   ├─ 2026-02-18 学习日报             [每日]
│   ├─ ...
│   ├─ 📊 第 08 周 周报 (02/17-02/23)  [周报]
│   └─ 📊 第 09 周 周报 (02/24-03/02)  [周报]
│
├─ 📈 2026 年 2 月 — 月度复盘         [月度复盘]
│
└─ 📅 2026 年 3 月学习日记             [月份页面]
```

---

## ⏰ 定时任务配置

| 任务 | Cron 表达式 | 时区 | 超时 | 模型 |
|------|------------|------|------|------|
| `learning-upgrade-daily` | `0 15 * * *` | Asia/Shanghai | 1800s | ark/kimi-k2.5 |
| `learning-upgrade-weekly` | `0 9 * * 1` | Asia/Shanghai | 2400s | ark/kimi-k2.5 |
| `learning-upgrade-monthly` | `0 10 1 * *` | Asia/Shanghai | 3600s | ark/kimi-k2.5 |

---

## 📁 目录结构

```
logs/
├── github-monitor/YYYYMMDD.md       # 每日 GitHub 报告
├── community-scraper/YYYYMMDD.md    # 每日社区报告
├── tech-analyzer/YYYYMMDD.md        # 每日技术分析
├── daily-digest/YYYYMMDD.md         # 每日汇总 (v3 新增)
├── weekly-review/YYYY-Wxx.md        # 周报 (v3 新增)
└── monthly-review/YYYY-MM.md        # 月报 (v3 新增)

tracker/                              # v3 新增
├── action-items.json                 # 行动项追踪
└── growth-metrics.json               # 成长指标
```

---

## 🔐 安全机制

| 机制 | 说明 |
|------|------|
| 环境变量隔离 | 从 `~/.openclaw/.env` 读取 |
| 提示词注入检测 | 8 种攻击模式检测 |
| 执行沙箱 | isolated 会话 + 超时限制 |
| 错误隔离 | 单步失败降级处理，不阻断全流程 |

---

## 🚀 使用指南

### 手动执行

```bash
# 每日流程
~/.openclaw/workspace/skills/learning-upgrade/tools/learning-daily.sh

# 周报流程
~/.openclaw/workspace/skills/learning-upgrade/tools/learning-weekly.sh

# 月报流程
~/.openclaw/workspace/skills/learning-upgrade/tools/learning-monthly.sh

# 行动项管理
python3 ~/.openclaw/workspace/skills/learning-upgrade/tools/action-tracker.py --list
python3 ~/.openclaw/workspace/skills/learning-upgrade/tools/action-tracker.py --stats
```

### 环境变量

```bash
# ~/.openclaw/.env (已有)
export GITHUB_TOKEN="ghp_xxx"
export MATON_API_KEY="K_xxx"
export ARK_API_KEY="xxx"
```

---

## 📊 新增 Cron Job 配置

### 周报 Cron

```json
{
  "name": "learning-upgrade-weekly",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "0 9 * * 1",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "执行学习改进周报任务：~/.openclaw/workspace/skills/learning-upgrade/tools/learning-weekly.sh",
    "model": "ark/kimi-k2.5",
    "timeoutSeconds": 2400
  },
  "delivery": {
    "mode": "announce",
    "channel": "telegram",
    "to": "1106494779"
  }
}
```

### 月报 Cron

```json
{
  "name": "learning-upgrade-monthly",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "0 10 1 * *",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "执行学习改进月报任务：~/.openclaw/workspace/skills/learning-upgrade/tools/learning-monthly.sh",
    "model": "ark/kimi-k2.5",
    "timeoutSeconds": 3600
  },
  "delivery": {
    "mode": "announce",
    "channel": "telegram",
    "to": "1106494779"
  }
}
```

---

*最后更新：2026-02-20 | 版本：3.0.0 (日/周/月三级复盘体系)*
