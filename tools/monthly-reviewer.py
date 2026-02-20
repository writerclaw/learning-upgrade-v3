#!/usr/bin/env python3
"""
每月复盘分析器 v3.0
功能：
  1. 加载上月全部周报
  2. 月度趋势分析
  3. 知识图谱 & 成长路径
  4. 下月学习规划建议
  5. Notion 月报页面
  6. Telegram 推送
"""

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import calendar

# === 路径配置 ===
WORKSPACE_DIR = Path("/home/writer/.openclaw/workspace")
LOGS_DIR = WORKSPACE_DIR / "logs"
SKILL_DIR = WORKSPACE_DIR / "skills" / "learning-upgrade"
TRACKER_DIR = SKILL_DIR / "tracker"
OUTPUT_DIR = LOGS_DIR / "monthly-review"

# === API 配置 ===
ARK_API_KEY = os.environ.get('ARK_API_KEY', '')
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MATON_API_KEY = os.environ.get('MATON_API_KEY', '')
MATON_BASE_URL = "https://gateway.maton.ai/v1"

# Notion 根页面 ID
LEARNING_DIARY_ROOT_ID = "1a09bfd6-0b4f-80d7-ab33-ca2e38e0d9f0"


def load_env():
    """加载环境变量"""
    env_file = Path("/home/writer/.openclaw/.env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    if line.startswith('export '):
                        line = line[7:]
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

    global ARK_API_KEY, MATON_API_KEY
    ARK_API_KEY = os.environ.get('ARK_API_KEY', ARK_API_KEY)
    MATON_API_KEY = os.environ.get('MATON_API_KEY', MATON_API_KEY)


def get_last_month_info():
    """获取上月信息"""
    today = datetime.now()
    # 上月的第一天
    first_of_this_month = today.replace(day=1)
    last_day_of_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_day_of_prev.replace(day=1)

    year = first_of_prev.year
    month = first_of_prev.month
    total_days = calendar.monthrange(year, month)[1]

    return {
        "year": year,
        "month": month,
        "year_month": f"{year}-{month:02d}",
        "year_month_cn": f"{year} 年 {month:02d} 月",
        "first_day": first_of_prev,
        "last_day": last_day_of_prev,
        "total_days": total_days
    }


def get_weeks_in_month(year, month):
    """获取某月包含的 ISO 周列表"""
    total_days = calendar.monthrange(year, month)[1]
    weeks = set()
    for day in range(1, total_days + 1):
        d = datetime(year, month, day)
        iso_week = d.isocalendar()[1]
        weeks.add(f"{year}-W{iso_week:02d}")
    return sorted(weeks)


def load_weekly_reports(year, month):
    """加载某月的所有周报"""
    weeks = get_weeks_in_month(year, month)
    weekly_dir = LOGS_DIR / "weekly-review"
    reports = []

    for week_id in weeks:
        md_file = weekly_dir / f"{week_id}.md"
        json_file = weekly_dir / f"{week_id}.json"

        weekly = {"week_id": week_id, "content": None, "analysis": None}

        if md_file.exists():
            with open(md_file, 'r', encoding='utf-8') as f:
                weekly["content"] = f.read()

        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                try:
                    weekly["analysis"] = json.load(f)
                except json.JSONDecodeError:
                    pass

        if weekly["content"] or weekly["analysis"]:
            reports.append(weekly)

    return reports


def load_daily_stats(year, month):
    """统计某月的每日学习情况"""
    total_days = calendar.monthrange(year, month)[1]
    learning_days = 0
    max_streak = 0
    current_streak = 0

    for day in range(1, total_days + 1):
        date_stamp = f"{year}{month:02d}{day:02d}"
        has_report = False

        for subdir in ["github-monitor", "community-scraper", "tech-analyzer"]:
            log_dir = LOGS_DIR / subdir
            # 检查各种可能的文件名格式
            for pattern in [f"{subdir}-{date_stamp}.md", f"tech-analysis-{date_stamp}.md"]:
                if (log_dir / pattern).exists():
                    has_report = True
                    break
            if has_report:
                break

        if has_report:
            learning_days += 1
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return {
        "total_days": total_days,
        "learning_days": learning_days,
        "max_streak": max_streak,
        "rate": round(learning_days / total_days, 2)
    }


def load_monthly_action_items(year_month):
    """加载某月的行动项"""
    action_file = TRACKER_DIR / "action-items.json"
    if not action_file.exists():
        return {"items": [], "total": 0, "done": 0, "completion_rate": 0}

    with open(action_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = [
        i for i in data.get("items", [])
        if i.get("source_date", "").startswith(year_month)
    ]

    done = sum(1 for i in items if i["status"] == "done")
    dropped = sum(1 for i in items if i["status"] == "dropped")
    total_active = len(items) - dropped

    return {
        "items": items,
        "total": len(items),
        "done": done,
        "dropped": dropped,
        "pending": sum(1 for i in items if i["status"] in ("pending", "in_progress")),
        "completion_rate": round(done / max(total_active, 1), 2)
    }


def llm_monthly_analysis(weekly_reports, daily_stats, action_items, month_info):
    """调用 LLM 进行月度综合分析"""

    # 汇总周报内容
    weekly_summaries = ""
    for wr in weekly_reports:
        if wr["content"]:
            weekly_summaries += f"\n--- {wr['week_id']} ---\n{wr['content'][:3000]}\n"

    prompt = f"""你是一位资深技术成长顾问。请基于以下一个月的学习数据进行全面复盘分析。

## 月份: {month_info['year_month_cn']}

## 学习投入统计
- 总天数: {daily_stats['total_days']}
- 学习天数: {daily_stats['learning_days']}
- 学习率: {daily_stats['rate'] * 100:.0f}%
- 最佳连续学习: {daily_stats['max_streak']} 天

## 行动项统计
- 总计: {action_items['total']} 项
- 已完成: {action_items['done']} 项
- 完成率: {action_items['completion_rate'] * 100:.0f}%

## 周报汇总 ({len(weekly_reports)} 周)
{weekly_summaries[:10000]}

## 请输出以下分析 (JSON 格式):

```json
{{
  "tech_evolution": [
    {{
      "week": "W01",
      "focus": "该周重点关注的技术方向",
      "key_learning": "关键收获"
    }}
  ],
  "source_quality": [
    {{
      "source": "信息源名称",
      "value_count": 有价值内容数量,
      "high_value_rate": 0.0到1.0,
      "rating": "1-5星评级",
      "suggestion": "改进建议"
    }}
  ],
  "knowledge_coverage": {{
    "covered_areas": ["已覆盖技术领域"],
    "deep_areas": ["深度学习的领域"],
    "blind_spots": ["应该关注但未关注的领域"],
    "depth_vs_breadth": "专精/均衡/泛学 的评估"
  }},
  "growth_assessment": {{
    "overall_score": 0到100,
    "strengths": ["本月做得好的方面"],
    "weaknesses": ["需要改进的方面"],
    "growth_curve": "上升/持平/下降"
  }},
  "next_month_plan": {{
    "focus_directions": [
      {{
        "direction": "重点方向",
        "reason": "为什么推荐",
        "resources": ["推荐资源"]
      }}
    ],
    "monthly_challenge": {{
      "title": "月度挑战目标",
      "description": "具体描述",
      "success_criteria": "成功标准"
    }},
    "avoid_pitfalls": ["需要避免的问题"]
  }}
}}
```
"""

    url = f"{ARK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4.7",
        "messages": [
            {"role": "system", "content": "你是一位技术成长导师，擅长从大量学习数据中提炼成长洞察和发展建议。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 5000
    }

    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        response = urllib.request.urlopen(req, context=ctx, timeout=300)
        result = json.load(response)
        content = result['choices'][0]['message']['content']

        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            return json.loads(content)
    except Exception as e:
        print(f"❌ LLM 分析失败: {e}")
        return None


def generate_monthly_report(month_info, daily_stats, weekly_reports, action_items, llm_analysis):
    """生成月度复盘 Markdown 报告"""

    md = []
    md.append(f"# 📈 {month_info['year_month_cn']} — 月度复盘")
    md.append("")
    md.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append("")

    # 月度统计
    md.append("## 📊 月度统计")
    md.append("")
    md.append(f"- 总学习天数: **{daily_stats['learning_days']}/{daily_stats['total_days']}** ({daily_stats['rate'] * 100:.0f}%)")
    md.append(f"- 周报覆盖: **{len(weekly_reports)} 周**")
    md.append(f"- 行动项完成率: **{action_items['completion_rate'] * 100:.0f}%** ({action_items['done']}/{action_items['total']})")
    md.append(f"- 最佳连续学习: **{daily_stats['max_streak']} 天**")
    md.append("")

    if llm_analysis:
        # 技术演进路径
        if llm_analysis.get("tech_evolution"):
            md.append("## 🗺️ 技术演进路径")
            md.append("")
            for week in llm_analysis["tech_evolution"]:
                md.append(f"- **{week['week']}**: {week['focus']}")
                md.append(f"  - 关键收获: {week['key_learning']}")
            md.append("")

        # 信息源质量评估
        if llm_analysis.get("source_quality"):
            md.append("## 📊 信息源质量评估")
            md.append("")
            md.append("| 信息源 | 有效内容 | 高价值占比 | 评级 | 建议 |")
            md.append("|--------|---------|-----------|------|------|")
            for src in llm_analysis["source_quality"]:
                stars = "⭐" * int(float(src.get("rating", "3")))
                rate = f"{float(src.get('high_value_rate', 0)) * 100:.0f}%"
                md.append(f"| {src['source']} | {src.get('value_count', '?')} | {rate} | {stars} | {src.get('suggestion', '-')} |")
            md.append("")

        # 知识覆盖分析
        if llm_analysis.get("knowledge_coverage"):
            kc = llm_analysis["knowledge_coverage"]
            md.append("## 🧠 知识覆盖分析")
            md.append("")
            md.append(f"**学习风格评估**: {kc.get('depth_vs_breadth', '未知')}")
            md.append("")
            if kc.get("covered_areas"):
                md.append(f"**已覆盖领域**: {', '.join(kc['covered_areas'])}")
            if kc.get("deep_areas"):
                md.append(f"**深度领域**: {', '.join(kc['deep_areas'])}")
            if kc.get("blind_spots"):
                md.append("")
                md.append("**⚠️ 知识盲区**:")
                for spot in kc["blind_spots"]:
                    md.append(f"  - {spot}")
            md.append("")

        # 成长评估
        if llm_analysis.get("growth_assessment"):
            ga = llm_analysis["growth_assessment"]
            md.append("## 📈 成长评估")
            md.append("")
            md.append(f"**综合评分**: {ga.get('overall_score', '?')}/100  |  **成长曲线**: {ga.get('growth_curve', '?')}")
            md.append("")
            if ga.get("strengths"):
                md.append("**✅ 做得好的**:")
                for s in ga["strengths"]:
                    md.append(f"  - {s}")
            if ga.get("weaknesses"):
                md.append("")
                md.append("**⚠️ 需改进的**:")
                for w in ga["weaknesses"]:
                    md.append(f"  - {w}")
            md.append("")

    # 行动项回顾
    md.append("## ✅ 月度行动项回顾")
    md.append("")
    if action_items["items"]:
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "dropped": "🗑️"}
        md.append("| 行动项 | 来源 | 优先级 | 状态 |")
        md.append("|--------|------|--------|------|")
        for item in action_items["items"][:20]:
            emoji = status_emoji.get(item["status"], "❓")
            md.append(f"| {item['title'][:35]} | {item.get('source', '-')} | {item['priority']} | {emoji} |")
        if len(action_items["items"]) > 20:
            md.append(f"| ... 还有 {len(action_items['items']) - 20} 项 | | | |")
    else:
        md.append("本月暂无行动项记录")
    md.append("")

    # 下月规划
    if llm_analysis and llm_analysis.get("next_month_plan"):
        nmp = llm_analysis["next_month_plan"]
        md.append("## 🎯 下月学习规划")
        md.append("")

        if nmp.get("focus_directions"):
            md.append("### 推荐重点方向")
            for i, fd in enumerate(nmp["focus_directions"], 1):
                md.append(f"**{i}. {fd['direction']}**")
                md.append(f"  - 原因: {fd['reason']}")
                if fd.get("resources"):
                    md.append(f"  - 资源: {', '.join(fd['resources'])}")
                md.append("")

        if nmp.get("monthly_challenge"):
            mc = nmp["monthly_challenge"]
            md.append("### 🏆 月度挑战")
            md.append(f"**{mc['title']}**")
            md.append(f"  {mc.get('description', '')}")
            md.append(f"  成功标准: {mc.get('success_criteria', '未定义')}")
            md.append("")

        if nmp.get("avoid_pitfalls"):
            md.append("### ⚠️ 需要避免")
            for pit in nmp["avoid_pitfalls"]:
                md.append(f"  - {pit}")
            md.append("")

    md.append("---")
    md.append("*自动生成于 Monthly Reviewer v3.0*")

    return '\n'.join(md)


def notion_request(endpoint, method='GET', data=None):
    """Notion API 请求"""
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


def create_monthly_notion_page(month_info, report_content):
    """在 Notion 创建月度复盘页面（放在根页面下）"""

    children = []

    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"📈 {month_info['year_month_cn']} — 月度复盘"}}]
        }
    })

    children.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"}}],
            "icon": {"emoji": "📈"}
        }
    })

    # 将报告内容转为 Notion blocks
    for line in report_content.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('# '):
            continue
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
        elif line.startswith('- '):
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:][:2000]}}]
                }
            })
        elif line.startswith('|') and '---' not in line:
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

    children = children[:95]

    page_title = f"📈 {month_info['year_month_cn']} — 月度复盘"

    page_data = {
        "parent": {"page_id": LEARNING_DIARY_ROOT_ID},
        "properties": {
            "title": [{"type": "text", "text": {"content": page_title}}]
        },
        "children": children
    }

    result = notion_request("pages", method='POST', data=page_data)
    return result


def update_growth_metrics(month_info, daily_stats, action_items, llm_analysis):
    """更新成长指标"""
    metrics_file = TRACKER_DIR / "growth-metrics.json"

    if metrics_file.exists():
        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
    else:
        metrics = {
            "monthly_stats": [],
            "updated_at": None
        }

    month_entry = {
        "month": month_info["year_month"],
        "learning_days": daily_stats["learning_days"],
        "total_days": daily_stats["total_days"],
        "learning_rate": daily_stats["rate"],
        "max_streak": daily_stats["max_streak"],
        "action_items_total": action_items["total"],
        "action_items_done": action_items["done"],
        "completion_rate": action_items["completion_rate"],
        "overall_score": llm_analysis.get("growth_assessment", {}).get("overall_score") if llm_analysis else None,
        "recorded_at": datetime.now().isoformat()
    }

    # 避免重复
    metrics["monthly_stats"] = [
        m for m in metrics.get("monthly_stats", [])
        if m.get("month") != month_info["year_month"]
    ]
    metrics["monthly_stats"].append(month_entry)
    metrics["updated_at"] = datetime.now().isoformat()

    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


# === 主流程 ===

def main():
    print("=" * 60)
    print("📈 Learning Upgrade — 每月复盘分析器 v3.0")
    print("=" * 60)

    load_env()

    month_info = get_last_month_info()
    print(f"\n📅 复盘月份: {month_info['year_month_cn']}")
    print(f"   日期范围: {month_info['first_day'].strftime('%Y-%m-%d')} ~ {month_info['last_day'].strftime('%Y-%m-%d')}")

    # Step 1: 加载周报
    print(f"\n📥 步骤 1/6: 加载上月周报...")
    weekly_reports = load_weekly_reports(month_info["year"], month_info["month"])
    print(f"  ✅ 加载 {len(weekly_reports)} 份周报")

    # Step 2: 统计每日学习
    print(f"\n📊 步骤 2/6: 统计每日学习情况...")
    daily_stats = load_daily_stats(month_info["year"], month_info["month"])
    print(f"  学习天数: {daily_stats['learning_days']}/{daily_stats['total_days']}")
    print(f"  最佳连续: {daily_stats['max_streak']} 天")

    # Step 3: 加载行动项
    print(f"\n✅ 步骤 3/6: 加载月度行动项...")
    action_items = load_monthly_action_items(month_info["year_month"])
    print(f"  总计: {action_items['total']}  完成: {action_items['done']}  完成率: {action_items['completion_rate'] * 100:.0f}%")

    # Step 4: LLM 分析
    print(f"\n🤖 步骤 4/6: LLM 月度综合分析...")
    llm_analysis = llm_monthly_analysis(weekly_reports, daily_stats, action_items, month_info)
    if llm_analysis:
        print("  ✅ 分析完成")
        if llm_analysis.get("growth_assessment"):
            print(f"    综合评分: {llm_analysis['growth_assessment'].get('overall_score', '?')}/100")
    else:
        print("  ⚠️ LLM 分析失败，使用基础数据")

    # Step 5: 生成报告 & Notion
    print(f"\n📝 步骤 5/6: 生成月报 & Notion 更新...")

    report_md = generate_monthly_report(
        month_info, daily_stats, weekly_reports, action_items, llm_analysis
    )

    # 保存本地
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUT_DIR / f"{month_info['year_month']}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"  ✅ 本地报告: {report_file}")

    if llm_analysis:
        json_file = OUTPUT_DIR / f"{month_info['year_month']}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(llm_analysis, f, ensure_ascii=False, indent=2)

    # 更新成长指标
    update_growth_metrics(month_info, daily_stats, action_items, llm_analysis)
    print(f"  ✅ 成长指标已更新")

    # Notion 月度复盘
    monthly_title = f"{month_info['year_month_cn']} — 月度复盘"
    existing = search_notion_page(monthly_title)
    if existing:
        print(f"  ⚠️ 月度复盘页面已存在，跳过创建")
    else:
        result = create_monthly_notion_page(month_info, report_md)
        if result:
            page_id = result.get('id', '')
            print(f"  ✅ Notion 月报创建成功: {page_id}")
        else:
            print(f"  ❌ Notion 月报创建失败")

    # Step 6: Telegram 摘要
    print(f"\n📱 步骤 6/6: Telegram 摘要...")
    tg_summary = generate_telegram_summary(month_info, daily_stats, action_items, llm_analysis)
    print(tg_summary)

    print(f"\n{'=' * 60}")
    print(f"🎉 月度复盘完成！({month_info['year_month']})")
    print(f"{'=' * 60}")


def generate_telegram_summary(month_info, daily_stats, action_items, llm_analysis):
    """生成 Telegram 推送摘要"""
    lines = []
    lines.append(f"📈 {month_info['year_month_cn']} 月度复盘完成")
    lines.append("")
    lines.append(f"📅 学习天数: {daily_stats['learning_days']}/{daily_stats['total_days']} ({daily_stats['rate'] * 100:.0f}%)")
    lines.append(f"🔥 最佳连续: {daily_stats['max_streak']} 天")
    lines.append(f"✅ 行动项完成率: {action_items['completion_rate'] * 100:.0f}%")

    if llm_analysis:
        ga = llm_analysis.get("growth_assessment", {})
        if ga.get("overall_score"):
            lines.append(f"📊 综合评分: {ga['overall_score']}/100 ({ga.get('growth_curve', '')})")

        nmp = llm_analysis.get("next_month_plan", {})
        focus = nmp.get("focus_directions", [])
        if focus:
            lines.append("")
            lines.append("🎯 下月重点:")
            for fd in focus[:3]:
                lines.append(f"  • {fd['direction']}")

        challenge = nmp.get("monthly_challenge", {})
        if challenge.get("title"):
            lines.append(f"\n🏆 月度挑战: {challenge['title']}")

    return '\n'.join(lines)


if __name__ == "__main__":
    main()
