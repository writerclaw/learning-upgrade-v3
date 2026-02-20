#!/usr/bin/env python3
"""
Notion 日记更新器 v3.0
变更：
  - 从 tech-analyzer 的 JSON 结果中动态读取行动项
  - 日记内容更丰富（不再硬编码）
  - 保留原有的月份页面 / 每日页面自动创建逻辑
"""

import json
import os
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

# === 配置 ===
WORKSPACE_DIR = Path("/home/writer/.openclaw/workspace")
LOGS_DIR = WORKSPACE_DIR / "logs"
SKILL_DIR = WORKSPACE_DIR / "skills" / "learning-upgrade"

MATON_API_KEY = os.environ.get('MATON_API_KEY', '')
MATON_BASE_URL = "https://gateway.maton.ai/notion/v1"

# Notion 学习日记根页面（使用 v2.0 验证过的 ID）
LEARNING_DIARY_ROOT_ID = os.environ.get("NOTION_ROOT_PAGE_ID", "30d80316-1300-803f-beab-fd599781e02c")


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
    global MATON_API_KEY
    MATON_API_KEY = os.environ.get('MATON_API_KEY', MATON_API_KEY)


def notion_request(endpoint, method='GET', data=None):
    """Notion API 请求"""
    url = f"{MATON_BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {MATON_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2025-09-03"
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


def search_page(title):
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


def create_month_page(year_month, parent_id):
    """创建月份页面"""
    page_data = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": [{"type": "text", "text": {"content": f"📅 {year_month}学习日记"}}]
        },
        "children": [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": f"{year_month}技术学习记录"}}],
                    "icon": {"emoji": "📅"}
                }
            }
        ]
    }
    return notion_request("pages", method='POST', data=page_data)


def load_daily_reports():
    """加载当日所有报告"""
    today = datetime.now().strftime('%Y%m%d')
    reports = {}

    # GitHub Monitor
    gh_file = LOGS_DIR / "github-monitor" / f"github-monitor-{today}.md"
    if gh_file.exists():
        with open(gh_file, 'r', encoding='utf-8') as f:
            reports['github'] = f.read()[:3000]
        print(f"  ✅ 加载 GitHub 报告")

    # Community Scraper
    comm_file = LOGS_DIR / "community-scraper" / f"community-scraper-{today}.md"
    if comm_file.exists():
        with open(comm_file, 'r', encoding='utf-8') as f:
            reports['community'] = f.read()[:3000]
        print(f"  ✅ 加载社区报告")

    # Tech Analyzer
    tech_file = LOGS_DIR / "tech-analyzer" / f"tech-analysis-{today}.md"
    if tech_file.exists():
        with open(tech_file, 'r', encoding='utf-8') as f:
            reports['tech'] = f.read()[:4000]
        print(f"  ✅ 加载技术分析报告")

    # Tech Analyzer JSON (v3.0: 用于提取行动项)
    tech_json = LOGS_DIR / "tech-analyzer" / f"tech-analysis-{today}.json"
    if tech_json.exists():
        with open(tech_json, 'r', encoding='utf-8') as f:
            try:
                reports['tech_json'] = json.load(f)
                print(f"  ✅ 加载技术分析 JSON")
            except json.JSONDecodeError:
                pass

    return reports


def extract_highlights(text, section_header, max_items=5):
    """从 Markdown 文本中提取某个章节的要点"""
    items = []
    in_section = False
    for line in text.split('\n'):
        if section_header.lower() in line.lower():
            in_section = True
            continue
        if in_section:
            if line.startswith('## ') or line.startswith('# '):
                break  # 进入下一个章节
            if line.strip().startswith('- '):
                items.append(line.strip()[2:].strip()[:200])
                if len(items) >= max_items:
                    break
    return items


def create_daily_page(date_str, parent_id, reports):
    """创建每日学习日报页面 (v3.0: 动态内容)"""
    children = []

    # 标题
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"📅 {date_str} 学习日报"}}]
        }
    })

    # 元数据
    children.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"}}],
            "icon": {"emoji": "🦞"}
        }
    })

    # === 今日技术动态 ===
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "📰 今日技术动态"}}]
        }
    })

    # GitHub 数据
    if 'github' in reports:
        # 动态提取 Stars 等数据
        for line in reports['github'].split('\n'):
            if 'Stars:' in line or 'Forks:' in line or '最新版本' in line:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line.strip().lstrip('- ').strip()[:200]}}]
                    }
                })
                if len(children) > 15:
                    break

    # 社区数据
    if 'community' in reports:
        items = extract_highlights(reports['community'], '资源总数', 3)
        items += extract_highlights(reports['community'], 'Hacker News', 3)
        for item in items[:3]:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": item[:200]}}]
                }
            })

    # === 关键技术洞察 ===
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "💡 关键技术洞察"}}]
        }
    })

    if 'tech_json' in reports:
        tech_data = reports['tech_json']

        # 架构亮点
        for highlight in tech_data.get('architecture_highlights', [])[:3]:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"🏗️ {highlight.get('title', '?')} (影响: {highlight.get('impact', '?')})"}}]
                }
            })

        # 安全趋势
        for trend in tech_data.get('security_trends', [])[:2]:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"🔒 {trend.get('trend', '?')} [{trend.get('priority', '?')}]"}}]
                }
            })

        # 创新机会
        for opp in tech_data.get('innovation_opportunities', [])[:2]:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"💡 {opp.get('opportunity', '?')} (可行性: {opp.get('feasibility', '?')})"}}]
                }
            })

    elif 'tech' in reports:
        # 降级: 从 Markdown 提取
        items = extract_highlights(reports['tech'], '架构设计亮点', 3)
        items += extract_highlights(reports['tech'], '安全趋势', 2)
        for item in items[:5]:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": item[:200]}}]
                }
            })

    # === 优先级行动项 (v3.0: 从 JSON 动态读取) ===
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "📋 优先级行动项"}}]
        }
    })

    if 'tech_json' in reports and 'action_items' in reports['tech_json']:
        for item in reports['tech_json']['action_items'][:5]:
            priority_tag = {"high": "[P0]", "medium": "[P1]", "low": "[P2]"}
            tag = priority_tag.get(item.get("priority", "medium"), "[P1]")
            children.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{tag} {item.get('title', '未命名')}"}}],
                    "checked": False
                }
            })
    else:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "今日暂无行动项"}}]
            }
        })

    # 分割线
    children.append({
        "object": "block",
        "type": "divider",
        "divider": {}
    })

    # 限制 blocks
    children = children[:95]

    # 创建页面
    page_data = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": [{"type": "text", "text": {"content": f"{date_str} 学习日报"}}]
        },
        "children": children
    }

    result = notion_request("pages", method='POST', data=page_data)
    return result


def main():
    print("🔍 加载每日报告...")
    load_env()
    reports = load_daily_reports()

    if not reports:
        print("❌ 未找到每日报告")
        return

    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    year_month = today.strftime('%Y 年 %m 月')

    print(f"\n🔍 搜索 {year_month} 页面...")
    month_page_id = search_page(year_month)

    if not month_page_id:
        print(f"📄 创建 {year_month} 页面...")
        month_result = create_month_page(year_month, LEARNING_DIARY_ROOT_ID)
        if month_result:
            month_page_id = month_result.get('id')
            print(f"✅ {year_month} 页面创建成功：{month_page_id}")
        else:
            print(f"❌ {year_month} 页面创建失败")
            return
    else:
        print(f"✅ 发现现有 {year_month} 页面：{month_page_id}")

    print(f"\n🔍 搜索 {date_str} 页面...")
    daily_page_id = search_page(date_str)

    if not daily_page_id:
        print(f"📄 创建 {date_str} 页面...")
        daily_result = create_daily_page(date_str, month_page_id, reports)
        if daily_result:
            daily_page_id = daily_result.get('id')
            print(f"✅ {date_str} 页面创建成功：{daily_page_id}")
            print(f"\n📄 页面结构：学习日记 → {year_month} → {date_str}")
            print(f"🔗 查看：https://www.notion.so/{daily_page_id.replace('-', '')}")
        else:
            print(f"❌ {date_str} 页面创建失败")
            return
    else:
        print(f"✅ {date_str} 页面已存在：{daily_page_id}")
        print("💡 跳过创建（如需更新请手动删除或修改）")

    print("\n🎉 Notion 更新完成！")


if __name__ == "__main__":
    main()
