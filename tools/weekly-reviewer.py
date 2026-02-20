#!/usr/bin/env python3
"""
每周复盘分析器 v3.0
功能：
  1. 加载上周全部日报
  2. 聚合分析 + 趋势识别
  3. 行动项完成检查
  4. LLM 生成改进行动列表
  5. Notion 周报页面
  6. Telegram 推送
"""

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# === 路径配置 ===
WORKSPACE_DIR = Path("/home/writer/.openclaw/workspace")
LOGS_DIR = WORKSPACE_DIR / "logs"
SKILL_DIR = WORKSPACE_DIR / "skills" / "learning-upgrade"
TRACKER_DIR = SKILL_DIR / "tracker"
OUTPUT_DIR = LOGS_DIR / "weekly-review"

# === API 配置 ===
ARK_API_KEY = os.environ.get('ARK_API_KEY', '')
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MATON_API_KEY = os.environ.get('MATON_API_KEY', '')
MATON_BASE_URL = "https://gateway.maton.ai/v1"

# Notion 根页面 ID
LEARNING_DIARY_ROOT_ID = "1a09bfd6-0b4f-80d7-ab33-ca2e38e0d9f0"

# === 工具函数 ===

def load_env():
    """加载环境变量"""
    env_file = Path("/home/writer/.openclaw/.env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    # 处理 export KEY=VALUE 和 KEY=VALUE 两种格式
                    if line.startswith('export '):
                        line = line[7:]
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

    global ARK_API_KEY, MATON_API_KEY
    ARK_API_KEY = os.environ.get('ARK_API_KEY', ARK_API_KEY)
    MATON_API_KEY = os.environ.get('MATON_API_KEY', MATON_API_KEY)


def get_last_week_range():
    """获取上周的日期范围 (周一~周日)"""
    today = datetime.now()
    # 找到本周一
    this_monday = today - timedelta(days=today.weekday())
    # 上周一 ~ 上周日
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday, last_sunday


def get_week_number(date):
    """获取 ISO 周数"""
    return f"{date.year}-W{date.isocalendar()[1]:02d}"


def load_daily_reports(start_date, end_date):
    """加载日期范围内的所有日报"""
    reports = []
    current = start_date

    while current <= end_date:
        date_stamp = current.strftime('%Y%m%d')
        date_str = current.strftime('%Y-%m-%d')

        daily = {"date": date_str, "sources": {}}

        # GitHub 报告
        gh_file = LOGS_DIR / "github-monitor" / f"github-monitor-{date_stamp}.md"
        if gh_file.exists():
            with open(gh_file, 'r', encoding='utf-8') as f:
                daily["sources"]["github"] = f.read()

        # 社区报告
        comm_file = LOGS_DIR / "community-scraper" / f"community-scraper-{date_stamp}.md"
        if comm_file.exists():
            with open(comm_file, 'r', encoding='utf-8') as f:
                daily["sources"]["community"] = f.read()

        # 技术分析
        tech_file = LOGS_DIR / "tech-analyzer" / f"tech-analysis-{date_stamp}.md"
        if tech_file.exists():
            with open(tech_file, 'r', encoding='utf-8') as f:
                daily["sources"]["tech"] = f.read()

        # 技术分析 JSON（如果有）
        tech_json = LOGS_DIR / "tech-analyzer" / f"tech-analysis-{date_stamp}.json"
        if tech_json.exists():
            with open(tech_json, 'r', encoding='utf-8') as f:
                try:
                    daily["sources"]["tech_json"] = json.load(f)
                except json.JSONDecodeError:
                    pass

        if daily["sources"]:
            reports.append(daily)

        current += timedelta(days=1)

    return reports


def load_action_items(week_id):
    """加载某周的行动项"""
    # 导入 action-tracker
    sys.path.insert(0, str(SKILL_DIR / "tools"))
    try:
        import importlib
        at = importlib.import_module("action-tracker")
        return at.check_items_by_week(week_id)
    except Exception as e:
        print(f"  ⚠️ 无法加载 action-tracker: {e}")
        # 直接读 JSON 文件
        action_file = TRACKER_DIR / "action-items.json"
        if action_file.exists():
            with open(action_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items = [i for i in data.get("items", []) if i.get("review_week") == week_id]
            return {
                "week": week_id,
                "items": items,
                "total": len(items),
                "done": sum(1 for i in items if i["status"] == "done"),
                "pending": sum(1 for i in items if i["status"] == "pending"),
                "completion_rate": round(
                    sum(1 for i in items if i["status"] == "done") / max(len(items), 1), 2
                )
            }
        return {"week": week_id, "items": [], "total": 0, "done": 0, "pending": 0, "completion_rate": 0}


def aggregate_analysis(reports):
    """聚合分析 - 提取关键信息"""

    all_text = ""
    tech_highlights = []
    github_events = []
    community_insights = []

    for report in reports:
        for source_type, content in report["sources"].items():
            if isinstance(content, str):
                all_text += f"\n--- {report['date']} {source_type} ---\n{content}\n"
            elif isinstance(content, dict) and source_type == "tech_json":
                # 从 JSON 提取结构化数据
                for highlight in content.get("architecture_highlights", []):
                    tech_highlights.append({
                        "date": report["date"],
                        "title": highlight.get("title", ""),
                        "impact": highlight.get("impact", "")
                    })

    return {
        "daily_count": len(reports),
        "dates": [r["date"] for r in reports],
        "combined_text": all_text[:15000],  # 限制长度
        "tech_highlights": tech_highlights,
        "missing_days": 7 - len(reports)
    }


def llm_weekly_analysis(aggregated_data, action_items_result):
    """调用 LLM 进行周度综合分析"""

    prompt = f"""你是一位资深技术学习顾问。请基于以下一周的技术学习内容进行综合分析。

## 本周学习数据

学习天数: {aggregated_data['daily_count']}/7
覆盖日期: {', '.join(aggregated_data['dates'])}
缺失天数: {aggregated_data['missing_days']}

## 本周行动项情况

总计: {action_items_result['total']} 项
已完成: {action_items_result['done']} 项
完成率: {action_items_result['completion_rate'] * 100:.0f}%

## 本周学习内容摘要

{aggregated_data['combined_text'][:8000]}

## 请输出以下分析 (JSON 格式):

```json
{{
  "tech_top5": [
    {{"topic": "话题名称", "frequency": 出现次数, "importance": "高/中/低"}}
  ],
  "key_events": [
    {{"event": "事件描述", "date": "日期", "significance": "重要性说明"}}
  ],
  "knowledge_gained": [
    {{"knowledge": "学到的知识点", "depth": "浅/中/深", "applicable": true/false}}
  ],
  "trends": [
    {{"trend": "趋势名称", "direction": "上升/下降/持平", "evidence": "证据"}}
  ],
  "improvement_actions": [
    {{
      "title": "改进方向",
      "priority": "high/medium/low",
      "expected_benefit": "预期收益",
      "steps": ["步骤1", "步骤2", "步骤3"],
      "expected_days": 7,
      "why_makes_stronger": "为什么这个改进能让你变得更强"
    }}
  ]
}}
```

改进建议要求:
1. 最多 5 项，按优先级排序
2. 每项必须有具体可执行的步骤
3. 重点识别能让人变得更强的高价值改进方向
4. 不要泛泛而谈，要针对本周具体内容
"""

    url = f"{ARK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4.7",
        "messages": [
            {"role": "system", "content": "你是一位技术学习顾问，擅长从学习内容中提炼高价值洞察和改进建议。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }

    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        response = urllib.request.urlopen(req, context=ctx, timeout=180)
        result = json.load(response)
        content = result['choices'][0]['message']['content']

        # 解析 JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            return json.loads(content)
    except Exception as e:
        print(f"❌ LLM 分析失败: {e}")
        return None


def generate_weekly_report(week_id, date_range, aggregated, action_items, llm_analysis):
    """生成 Markdown 格式周报"""
    start_str = date_range[0].strftime('%m/%d')
    end_str = date_range[1].strftime('%m/%d')
    week_num = date_range[0].isocalendar()[1]

    md = []
    md.append(f"# 📊 第 {week_num:02d} 周 周报 ({start_str} - {end_str})")
    md.append("")
    md.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append("")

    # 本周概览
    md.append("## 本周概览")
    md.append(f"- 学习天数: {aggregated['daily_count']}/7")
    md.append(f"- 行动项完成率: {action_items['completion_rate'] * 100:.0f}%")
    if llm_analysis:
        md.append(f"- 新发现技术: {len(llm_analysis.get('knowledge_gained', []))} 项")
    md.append("")

    if llm_analysis:
        # 技术热度 TOP 5
        if llm_analysis.get("tech_top5"):
            md.append("## 🔥 技术热度 TOP 5")
            md.append("")
            for i, topic in enumerate(llm_analysis["tech_top5"][:5], 1):
                md.append(f"{i}. **{topic['topic']}** — 重要性: {topic['importance']}")
            md.append("")

        # 关键事件
        if llm_analysis.get("key_events"):
            md.append("## 📰 关键事件")
            md.append("")
            for event in llm_analysis["key_events"]:
                md.append(f"- [{event.get('date', '')}] {event['event']}")
            md.append("")

        # 本周知识收获
        if llm_analysis.get("knowledge_gained"):
            md.append("## 🧠 本周知识收获")
            md.append("")
            for k in llm_analysis["knowledge_gained"]:
                applicable = "✅ 可应用" if k.get("applicable") else "📖 待深入"
                md.append(f"- {k['knowledge']} (深度: {k['depth']}) — {applicable}")
            md.append("")

    # 行动项检查
    md.append("## ✅ 行动项检查")
    md.append("")
    if action_items["items"]:
        md.append("| 行动项 | 优先级 | 状态 | 预期完成 |")
        md.append("|--------|--------|------|---------|")
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "dropped": "🗑️"}
        for item in action_items["items"]:
            emoji = status_emoji.get(item["status"], "❓")
            md.append(f"| {item['title'][:40]} | {item['priority']} | {emoji} {item['status']} | {item.get('expected_by', '-')} |")
        md.append("")
        md.append(f"**完成率**: {action_items['completion_rate'] * 100:.0f}% ({action_items['done']}/{action_items['total']})")
    else:
        md.append("本周暂无行动项记录")
    md.append("")

    # 改进行动列表
    if llm_analysis and llm_analysis.get("improvement_actions"):
        md.append("## 🚀 改进行动列表")
        md.append("")
        for i, action in enumerate(llm_analysis["improvement_actions"][:5], 1):
            priority_map = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
            priority_label = priority_map.get(action.get("priority", "medium"), "🟡 中")
            md.append(f"### {i}. {action['title']} [{priority_label}]")
            md.append(f"**预期收益**: {action.get('expected_benefit', '未知')}")
            md.append(f"**为什么能变强**: {action.get('why_makes_stronger', '未知')}")
            md.append("")
            if action.get("steps"):
                md.append("**具体步骤**:")
                for step in action["steps"]:
                    md.append(f"  - [ ] {step}")
            md.append("")

    # 趋势洞察
    if llm_analysis and llm_analysis.get("trends"):
        md.append("## 📈 趋势洞察")
        md.append("")
        for trend in llm_analysis["trends"]:
            direction_emoji = {"上升": "📈", "下降": "📉", "持平": "➡️"}
            emoji = direction_emoji.get(trend.get("direction", ""), "❓")
            md.append(f"- {emoji} **{trend['trend']}** ({trend['direction']})")
            md.append(f"  - 证据: {trend.get('evidence', '无')}")
        md.append("")

    md.append("---")
    md.append("*自动生成于 Weekly Reviewer v3.0*")

    return '\n'.join(md)


def notion_request(endpoint, method='GET', data=None):
    """Notion API 请求 (通过 Maton Gateway)"""
    url = f"{MATON_BASE_URL}/notion/{endpoint}"
    headers = {
        "Authorization": f"Bearer {MATON_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    ctx = ssl.create_default_context()
    try:
        req_data = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        response = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.load(response)
    except Exception as e:
        print(f"❌ Notion 请求失败: {e}")
        return None


def search_notion_page(title):
    """搜索 Notion 页面"""
    result = notion_request("search", method='POST', data={
        "query": title,
        "filter": {"property": "object", "value": "page"}
    })
    if result and result.get("results"):
        for page in result["results"]:
            page_title = ""
            props = page.get("properties", {})
            if "title" in props:
                title_arr = props["title"].get("title", [])
                if title_arr:
                    page_title = title_arr[0].get("plain_text", "")
            if title in page_title:
                return page.get("id")
    return None


def create_weekly_notion_page(week_num, start_str, end_str, month_page_id, report_content):
    """在 Notion 创建周报页面"""

    # 将 markdown 内容转为 Notion blocks
    children = []

    # 标题
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"📊 第 {week_num:02d} 周 周报 ({start_str} - {end_str})"}}]
        }
    })

    # 元数据
    children.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"}}],
            "icon": {"emoji": "📊"}
        }
    })

    # 报告内容按段落添加
    for line in report_content.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('# '):
            continue  # 跳过顶级标题
        elif line.startswith('## '):
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith('### '):
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        elif line.startswith('- [ ] '):
            children.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line[6:]}}],
                    "checked": False
                }
            })
        elif line.startswith('- [x] '):
            children.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line[6:]}}],
                    "checked": True
                }
            })
        elif line.startswith('- '):
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:][:2000]}}]
                }
            })
        elif line.startswith('|') and '---' not in line:
            # 表格行 → 转为文本
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                }
            })
        elif line.startswith('**') and line.endswith('**'):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                }
            })
        elif line == '---':
            children.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        elif len(line) > 2:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                }
            })

    # 限制 blocks 数量（Notion API 限制 100）
    children = children[:95]

    page_title = f"📊 第 {week_num:02d} 周 周报 ({start_str}-{end_str})"

    page_data = {
        "parent": {"page_id": month_page_id},
        "properties": {
            "title": [{"type": "text", "text": {"content": page_title}}]
        },
        "children": children
    }

    result = notion_request("pages", method='POST', data=page_data)
    return result


def save_improvement_actions(llm_analysis, week_id):
    """将改进行动项保存到 tracker"""
    if not llm_analysis or not llm_analysis.get("improvement_actions"):
        return

    sys.path.insert(0, str(SKILL_DIR / "tools"))
    try:
        import importlib
        at = importlib.import_module("action-tracker")

        for action in llm_analysis["improvement_actions"][:5]:
            at.add_item(
                title=action["title"],
                priority=action.get("priority", "medium"),
                source="weekly",
                steps=action.get("steps", []),
                expected_days=action.get("expected_days", 7)
            )
        print(f"✅ 已保存 {min(len(llm_analysis['improvement_actions']), 5)} 个改进行动项")
    except Exception as e:
        print(f"⚠️ 保存行动项失败: {e}")


# === 主流程 ===

def main():
    print("=" * 60)
    print("📊 Learning Upgrade — 每周复盘分析器 v3.0")
    print("=" * 60)

    # 加载环境变量
    load_env()

    # 获取上周日期范围
    last_monday, last_sunday = get_last_week_range()
    week_id = get_week_number(last_monday)
    start_str = last_monday.strftime('%m/%d')
    end_str = last_sunday.strftime('%m/%d')
    week_num = last_monday.isocalendar()[1]

    print(f"\n📅 复盘范围: {last_monday.strftime('%Y-%m-%d')} ~ {last_sunday.strftime('%Y-%m-%d')} ({week_id})")

    # Step 1: 加载日报
    print(f"\n📥 步骤 1/6: 加载上周日报...")
    reports = load_daily_reports(last_monday, last_sunday)
    print(f"  ✅ 加载 {len(reports)}/7 天日报")

    if not reports:
        print("  ❌ 未找到任何日报数据，跳过本周复盘")
        return

    # Step 2: 聚合分析
    print(f"\n📊 步骤 2/6: 聚合分析...")
    aggregated = aggregate_analysis(reports)
    print(f"  ✅ 聚合完成（{aggregated['daily_count']} 天，缺失 {aggregated['missing_days']} 天）")

    # Step 3: 行动项检查
    print(f"\n✅ 步骤 3/6: 行动项完成检查...")
    action_items = load_action_items(week_id)
    print(f"  总计: {action_items['total']}  完成: {action_items['done']}  完成率: {action_items['completion_rate'] * 100:.0f}%")

    # Step 4: LLM 分析
    print(f"\n🤖 步骤 4/6: LLM 深度分析...")
    llm_analysis = llm_weekly_analysis(aggregated, action_items)
    if llm_analysis:
        print(f"  ✅ 分析完成")
        print(f"    - 技术热度: {len(llm_analysis.get('tech_top5', []))} 项")
        print(f"    - 关键事件: {len(llm_analysis.get('key_events', []))} 个")
        print(f"    - 知识收获: {len(llm_analysis.get('knowledge_gained', []))} 点")
        print(f"    - 改进建议: {len(llm_analysis.get('improvement_actions', []))} 项")

        # 保存改进行动项到 tracker
        save_improvement_actions(llm_analysis, week_id)
    else:
        print("  ⚠️ LLM 分析失败，使用基础数据生成报告")

    # Step 5: 生成报告 & Notion
    print(f"\n📝 步骤 5/6: 生成周报 & Notion 更新...")

    # 生成 Markdown 报告
    report_md = generate_weekly_report(
        week_id, (last_monday, last_sunday),
        aggregated, action_items, llm_analysis
    )

    # 保存本地文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUT_DIR / f"{week_id}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"  ✅ 本地报告: {report_file}")

    # 保存 JSON 分析结果
    if llm_analysis:
        json_file = OUTPUT_DIR / f"{week_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(llm_analysis, f, ensure_ascii=False, indent=2)

    # Notion 周报
    year_month = last_monday.strftime('%Y 年 %m 月')
    print(f"  🔍 搜索 {year_month} 页面...")
    month_page_id = search_notion_page(year_month)

    if month_page_id:
        print(f"  ✅ 发现月份页面: {month_page_id}")

        # 检查周报页面是否已存在
        weekly_title = f"第 {week_num:02d} 周"
        existing = search_notion_page(weekly_title)
        if existing:
            print(f"  ⚠️ 周报页面已存在，跳过创建")
        else:
            result = create_weekly_notion_page(
                week_num, start_str, end_str,
                month_page_id, report_md
            )
            if result:
                page_id = result.get('id', '')
                print(f"  ✅ Notion 周报创建成功: {page_id}")
            else:
                print(f"  ❌ Notion 周报创建失败")
    else:
        print(f"  ⚠️ 未找到 {year_month} 页面，跳过 Notion 更新")

    # Step 6: 生成 Telegram 摘要
    print(f"\n📱 步骤 6/6: 生成 Telegram 摘要...")
    tg_summary = generate_telegram_summary(
        week_id, week_num, start_str, end_str,
        aggregated, action_items, llm_analysis
    )
    print(tg_summary)

    print(f"\n{'=' * 60}")
    print(f"🎉 每周复盘完成！({week_id})")
    print(f"{'=' * 60}")


def generate_telegram_summary(week_id, week_num, start_str, end_str, aggregated, action_items, llm_analysis):
    """生成 Telegram 推送摘要"""
    lines = []
    lines.append(f"📊 第 {week_num:02d} 周 复盘完成 ({start_str}-{end_str})")
    lines.append("")
    lines.append(f"📅 学习天数: {aggregated['daily_count']}/7")
    lines.append(f"✅ 行动项完成率: {action_items['completion_rate'] * 100:.0f}%")

    if llm_analysis:
        # TOP 3 技术热度
        top_techs = llm_analysis.get("tech_top5", [])[:3]
        if top_techs:
            lines.append("")
            lines.append("🔥 本周技术热度:")
            for t in top_techs:
                lines.append(f"  • {t['topic']}")

        # TOP 改进建议
        improvements = llm_analysis.get("improvement_actions", [])[:3]
        if improvements:
            lines.append("")
            lines.append("🚀 重点改进:")
            for imp in improvements:
                lines.append(f"  • {imp['title']}")

    return '\n'.join(lines)


if __name__ == "__main__":
    main()
