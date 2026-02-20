#!/usr/bin/env python3
"""
技术深度分析器 v3.0
变更：在原有分析基础上增加 action_items 输出
     行动项自动写入 tracker/action-items.json
"""

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# === 路径配置 ===
WORKSPACE_DIR = Path("/home/writer/.openclaw/workspace")
LOGS_DIR = WORKSPACE_DIR / "logs"
OUTPUT_DIR = LOGS_DIR / "tech-analyzer"
SKILL_DIR = WORKSPACE_DIR / "skills" / "learning-upgrade"

# === API 配置 ===
ARK_API_KEY = os.environ.get('ARK_API_KEY', '')
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"

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
    global ARK_API_KEY
    ARK_API_KEY = os.environ.get('ARK_API_KEY', ARK_API_KEY)


def load_daily_reports():
    """加载当日的 GitHub 和社区报告"""
    today = datetime.now().strftime('%Y%m%d')
    reports = {}

    gh_file = LOGS_DIR / "github-monitor" / f"github-monitor-{today}.md"
    if gh_file.exists():
        with open(gh_file, 'r', encoding='utf-8') as f:
            reports['github'] = f.read()[:3000]
        print("  ✅ 加载 GitHub 报告")

    comm_file = LOGS_DIR / "community-scraper" / f"community-scraper-{today}.md"
    if comm_file.exists():
        with open(comm_file, 'r', encoding='utf-8') as f:
            reports['community'] = f.read()[:3000]
        print("  ✅ 加载社区报告")

    # JSON 格式的 GitHub 报告（更结构化）
    gh_json = LOGS_DIR / "github-monitor" / f"github-monitor-{today}.json"
    if gh_json.exists():
        with open(gh_json, 'r', encoding='utf-8') as f:
            try:
                reports['github_json'] = json.load(f)
            except json.JSONDecodeError:
                pass

    comm_json = LOGS_DIR / "community-scraper" / f"community-scraper-{today}.json"
    if comm_json.exists():
        with open(comm_json, 'r', encoding='utf-8') as f:
            try:
                reports['community_json'] = json.load(f)
            except json.JSONDecodeError:
                pass

    return reports


def extract_technical_content(reports):
    """提取技术内容"""
    content = []

    # 从 GitHub JSON 提取
    if 'github_json' in reports:
        gh = reports['github_json']
        repos = gh.get('repos', {})

        # 主仓库数据
        main_repo = repos.get('main', {})
        for rel in main_repo.get('releases', []):
            content.append({
                "source": "GitHub Release",
                "title": f"{rel['tag']} - {rel['name']}",
                "date": rel.get('published_at', ''),
                "details": rel.get('body', '')[:500]
            })

        for topic in main_repo.get('trending_topics', []):
            content.append({
                "source": "GitHub Issue",
                "title": topic.get('title', ''),
                "comments": topic.get('comments', 0),
                "labels": ', '.join(topic.get('labels', []))
            })

        if main_repo.get('stars'):
            content.append({
                "source": "GitHub Stats",
                "stars": main_repo['stars'].get('stars', 0),
                "forks": main_repo['stars'].get('forks', 0),
                "open_issues": main_repo['stars'].get('open_issues', 0)
            })

    # 从社区 JSON 提取
    if 'community_json' in reports:
        comm = reports['community_json']
        sources = comm.get('sources', {})

        awesome = sources.get('awesome-openclaw', {})
        if awesome:
            content.append({
                "source": "awesome-openclaw",
                "total_resources": awesome.get('total_resources', 0),
                "categories": awesome.get('category_count', 0)
            })

        hn = sources.get('hacker-news', {})
        for story in hn.get('ai_stories', [])[:5]:
            content.append({
                "source": "Hacker News",
                "title": story.get('title', ''),
                "score": story.get('score', 0),
                "comments": story.get('comments', 0)
            })

        clawhub = sources.get('clawhub', {})
        if clawhub:
            content.append({
                "source": "ClawHub",
                "stars": clawhub.get('stars', 0),
                "forks": clawhub.get('forks', 0)
            })

    return content


def analyze_with_llm(technical_content):
    """使用 LLM 进行技术深度分析 (v3.0: 增加 action_items)"""

    prompt = """你是一位资深的 AI 架构师和技术分析师。请分析以下 OpenClaw 技术动态，并输出深度洞察：

## 技术内容
"""

    for item in technical_content[:10]:
        prompt += f"\n### {item['source']}\n"
        for key, value in item.items():
            if key != 'source':
                prompt += f"- {key}: {value}\n"

    prompt += """

## 分析要求

请按以下维度输出分析结果（JSON 格式）：

```json
{
  "architecture_highlights": [
    {
      "title": "架构设计亮点",
      "description": "详细描述",
      "impact": "高/中/低",
      "relevance_to_us": "与我们当前架构的相关性"
    }
  ],
  "security_trends": [
    {
      "trend": "安全趋势",
      "details": "详细说明",
      "priority": "P0/P1/P2",
      "action_required": "是否需要立即行动"
    }
  ],
  "performance_optimizations": [
    {
      "area": "性能优化领域",
      "technique": "技术方法",
      "estimated_improvement": "预估提升"
    }
  ],
  "community_patterns": [
    {
      "pattern": "社区模式",
      "evidence": "证据",
      "implication": "对我们的启示"
    }
  ],
  "technical_debt_risks": [
    {
      "risk": "技术债务风险",
      "severity": "严重/中等/轻微",
      "mitigation": "缓解措施"
    }
  ],
  "innovation_opportunities": [
    {
      "opportunity": "创新机会",
      "feasibility": "可行性（高/中/低）",
      "effort": "预计工作量",
      "value": "业务价值"
    }
  ],
  "action_items": [
    {
      "title": "具体行动项标题",
      "priority": "high/medium/low",
      "steps": ["步骤1", "步骤2", "步骤3"],
      "expected_days": 7,
      "reason": "为什么需要做这件事"
    }
  ]
}
```

请确保：
1. 分析深入、具体、可执行
2. action_items 是你从分析中提炼出的最重要的 2-3 个改进行动
3. 每个 action_item 必须有具体的执行步骤
"""

    url = f"{ARK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4.7",
        "messages": [
            {
                "role": "system",
                "content": "你是一位资深的 AI 架构师和技术分析师，擅长从技术动态中提取深度洞察和架构优化建议。"
            },
            {
                "role": "user",
                "content": prompt
            }
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

        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group(1))
        else:
            analysis = json.loads(content)

        return analysis

    except Exception as e:
        print(f"❌ LLM 分析失败：{e}")
        return None


def save_action_items(analysis):
    """将分析结果中的行动项保存到 tracker (v3.0 新增)"""
    action_items = analysis.get("action_items", [])
    if not action_items:
        print("  ℹ️ 本次分析无行动项输出")
        return

    sys.path.insert(0, str(SKILL_DIR / "tools"))
    try:
        import importlib
        # 动态导入（文件名包含连字符）
        spec = importlib.util.spec_from_file_location(
            "action_tracker",
            SKILL_DIR / "tools" / "action-tracker.py"
        )
        at = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(at)

        for item in action_items[:3]:  # 每天最多 3 个行动项
            at.add_item(
                title=item.get("title", "未命名"),
                priority=item.get("priority", "medium"),
                source="daily",
                steps=item.get("steps", []),
                expected_days=item.get("expected_days", 7)
            )
        print(f"  ✅ 已保存 {min(len(action_items), 3)} 个行动项到 tracker")
    except Exception as e:
        print(f"  ⚠️ 保存行动项失败: {e}")
        # 降级: 直接写入 JSON
        try:
            tracker_file = SKILL_DIR / "tracker" / "action-items.json"
            tracker_file.parent.mkdir(parents=True, exist_ok=True)

            if tracker_file.exists():
                with open(tracker_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"items": [], "stats": {}}

            today = datetime.now().strftime('%Y-%m-%d')
            week_num = datetime.now().isocalendar()[1]

            for i, item in enumerate(action_items[:3]):
                data["items"].append({
                    "id": f"AI-{today.replace('-', '')}-{len(data['items']) + 1:03d}",
                    "title": item.get("title", ""),
                    "source": "daily",
                    "source_date": today,
                    "priority": item.get("priority", "medium"),
                    "status": "pending",
                    "steps": item.get("steps", []),
                    "created_at": datetime.now().isoformat(),
                    "completed_at": None,
                    "review_week": f"{datetime.now().year}-W{week_num:02d}"
                })

            with open(tracker_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 降级保存行动项成功")
        except Exception as e2:
            print(f"  ❌ 降级保存也失败: {e2}")


def generate_tech_insight_report(analysis):
    """生成技术洞察报告"""
    if not analysis:
        return "❌ LLM 分析失败"

    report = []
    report.append("# 技术深度洞察报告")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    # 架构设计亮点
    if 'architecture_highlights' in analysis:
        report.append("## 🏗️ 架构设计亮点")
        report.append("")
        for i, highlight in enumerate(analysis['architecture_highlights'], 1):
            report.append(f"### {i}. {highlight['title']}")
            report.append(f"**影响**: {highlight.get('impact', '未知')}")
            report.append(f"**相关性**: {highlight.get('relevance_to_us', '未知')}")
            report.append("")
            report.append(highlight['description'])
            report.append("")

    # 安全趋势
    if 'security_trends' in analysis:
        report.append("## 🔒 安全趋势")
        report.append("")
        for trend in analysis['security_trends']:
            report.append(f"- **{trend['trend']}** [{trend['priority']}]")
            report.append(f"  - {trend['details']}")
            if trend.get('action_required'):
                report.append(f"  - ⚠️ **需要立即行动**")
            report.append("")

    # 性能优化
    if 'performance_optimizations' in analysis:
        report.append("## ⚡ 性能优化")
        report.append("")
        for opt in analysis['performance_optimizations']:
            report.append(f"- **{opt['area']}**")
            report.append(f"  - 技术：{opt['technique']}")
            report.append(f"  - 预估提升：{opt.get('estimated_improvement', '未知')}")
            report.append("")

    # 社区模式
    if 'community_patterns' in analysis:
        report.append("## 👥 社区模式")
        report.append("")
        for pattern in analysis['community_patterns']:
            report.append(f"- **{pattern['pattern']}**")
            report.append(f"  - 证据：{pattern.get('evidence', '无')}")
            report.append(f"  - 启示：{pattern.get('implication', '无')}")
            report.append("")

    # 技术债务风险
    if 'technical_debt_risks' in analysis:
        report.append("## ⚠️ 技术债务风险")
        report.append("")
        for risk in analysis['technical_debt_risks']:
            report.append(f"- **{risk['risk']}** [{risk['severity']}]")
            report.append(f"  - 缓解：{risk.get('mitigation', '无')}")
            report.append("")

    # 创新机会
    if 'innovation_opportunities' in analysis:
        report.append("## 💡 创新机会")
        report.append("")
        for opp in analysis['innovation_opportunities']:
            report.append(f"- **{opp['opportunity']}**")
            report.append(f"  - 可行性：{opp.get('feasibility', '未知')}")
            report.append(f"  - 工作量：{opp.get('effort', '未知')}")
            report.append(f"  - 价值：{opp.get('value', '未知')}")
            report.append("")

    # 行动项 (v3.0 新增)
    if 'action_items' in analysis:
        report.append("## 📋 今日行动项")
        report.append("")
        for item in analysis['action_items']:
            priority_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            emoji = priority_map.get(item.get("priority", "medium"), "🟡")
            report.append(f"### {emoji} {item['title']}")
            report.append(f"**原因**: {item.get('reason', '未说明')}")
            if item.get("steps"):
                for step in item["steps"]:
                    report.append(f"  - [ ] {step}")
            report.append("")

    return '\n'.join(report)


def main():
    print("🔍 加载每日报告...")
    load_env()
    reports = load_daily_reports()

    if not reports:
        print("❌ 未找到每日报告")
        return

    print("\n📊 提取技术内容...")
    tech_content = extract_technical_content(reports)
    print(f"  提取 {len(tech_content)} 条技术内容")

    print("\n🤖 调用 LLM 进行深度分析...")
    analysis = analyze_with_llm(tech_content)

    if not analysis:
        print("❌ LLM 分析失败")
        return

    print(f"  ✅ 分析完成")
    print(f"  - 架构亮点：{len(analysis.get('architecture_highlights', []))} 个")
    print(f"  - 安全趋势：{len(analysis.get('security_trends', []))} 个")
    print(f"  - 性能优化：{len(analysis.get('performance_optimizations', []))} 个")
    print(f"  - 创新机会：{len(analysis.get('innovation_opportunities', []))} 个")
    print(f"  - 行动项：{len(analysis.get('action_items', []))} 个")

    # v3.0: 保存行动项到 tracker
    print("\n📋 保存行动项...")
    save_action_items(analysis)

    print("\n📝 生成技术洞察报告...")
    report = generate_tech_insight_report(analysis)

    # 保存报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    output_file = OUTPUT_DIR / f"tech-analysis-{today}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 报告已保存：{output_file}")

    # 保存 JSON 分析结果
    json_file = OUTPUT_DIR / f"tech-analysis-{today}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已保存：{json_file}")

    print("\n🎉 技术深度分析完成！")


if __name__ == "__main__":
    main()
