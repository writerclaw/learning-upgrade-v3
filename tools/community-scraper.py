#!/usr/bin/env python3
"""
Community Scraper - OpenClaw 社区内容抓取
功能：
1. 抓取 awesome-openclaw 社区资源
2. 监控 ClawHub 技能动态
3. 追踪技术社区讨论（Hacker News 等）
4. 生成社区趋势报告

安全：
- 从环境变量读取密钥
- 外部内容仅作为数据处理
- 超时限制防止 hangs
"""

import urllib.request
import json
import ssl
import os
import re
from datetime import datetime
from pathlib import Path

# ==================== 安全机制 ====================

def detect_injection(content: str) -> bool:
    """检测潜在的提示词注入模式"""
    patterns = [
        r"ignore\s+previous\s+instructions",
        r"disregard\s+all",
        r"you\s+are\s+now",
        r"bypass\s+safety",
    ]
    lower_content = content.lower()
    for pattern in patterns:
        if re.search(pattern, lower_content):
            print(f"⚠️  检测到潜在的提示词注入模式")
            return True
    return False

# 配置
# 从环境变量读取 GitHub Token
import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN 环境变量未设置，请在 ~/.openclaw/.env 中配置")
OUTPUT_DIR = Path("/home/writer/.openclaw/workspace/logs/community-scraper")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def github_api(endpoint):
    """GitHub API 请求"""
    url = f"https://api.github.com/{endpoint}"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    
    ctx = ssl.create_default_context()
    try:
        response = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.load(response)
    except Exception as e:
        print(f"❌ API 请求失败：{e}")
        return None

def fetch_awesome_openclaw():
    """抓取 awesome-openclaw 资源列表"""
    print("  📚 抓取 awesome-openclaw...")
    
    # 获取 README 内容
    data = github_api("repos/SamurAIGPT/awesome-openclaw/readme")
    if not data:
        return None
    
    # 解码 README
    import base64
    content = base64.b64decode(data['content']).decode('utf-8')
    
    # 解析资源分类
    categories = {}
    current_category = None
    
    for line in content.split('\n'):
        if line.startswith('## '):
            current_category = line.replace('## ', '').strip()
            categories[current_category] = []
        elif line.startswith('- [') and current_category:
            # 提取资源链接
            try:
                title_start = line.find('[') + 1
                title_end = line.find(']')
                url_start = line.find('(') + 1
                url_end = line.find(')')
                
                if title_end > title_start and url_end > url_start:
                    title = line[title_start:title_end]
                    url = line[url_start:url_end]
                    categories[current_category].append({
                        "title": title,
                        "url": url
                    })
            except:
                pass
    
    return {
        "categories": categories,
        "total_resources": sum(len(v) for v in categories.values()),
        "category_count": len(categories)
    }

def fetch_clawhub_skills():
    """抓取 ClawHub 技能统计"""
    print("  🛠️  抓取 ClawHub 技能...")
    
    # ClawHub 没有公开 API，通过 GitHub skills 仓库估算
    data = github_api("repos/openclaw/skills")
    if not data:
        return None
    
    return {
        "stars": data.get('stargazers_count', 0),
        "forks": data.get('forks_count', 0),
        "url": data.get('html_url', ''),
        "description": data.get('description', '')
    }

def fetch_hacker_news_ai():
    """抓取 Hacker News AI 相关讨论"""
    print("  📰 抓取 Hacker News...")
    
    # 重试机制函数
    def fetch_with_retry(url, timeout=10, max_retries=3):
        for attempt in range(max_retries):
            try:
                ctx = ssl.create_default_context()
                response = urllib.request.urlopen(url, context=ctx, timeout=timeout)
                return json.load(response)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    ⚠️  重试 {attempt + 1}/{max_retries}...")
                    import time
                    time.sleep(1)
                else:
                    raise e
        return None
    
    # Hacker News API
    try:
        # 获取热门故事（带重试）
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_ids = fetch_with_retry(top_stories_url, timeout=10)[:50]  # 前 50 个
        
        # 获取故事详情并过滤 AI 相关
        ai_stories = []
        for story_id in top_ids[:20]:  # 检查前 20 个
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            try:
                story = fetch_with_retry(story_url, timeout=5)
                
                # 检查标题是否包含 AI 关键词
                title = story.get('title', '').lower()
                if any(kw in title for kw in ['ai', 'agent', 'openclaw', 'llm', 'gpt', 'claude']):
                    ai_stories.append({
                        "title": story.get('title', ''),
                        "url": story.get('url', ''),
                        "score": story.get('score', 0),
                        "comments": story.get('descendants', 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={story_id}"
                    })
            except:
                pass
        
        return ai_stories
    except Exception as e:
        print(f"    ⚠️  HN 抓取失败：{e}")
        return []

def generate_community_report():
    """生成社区趋势报告"""
    print("🔍 开始社区内容抓取...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "sources": {}
    }
    
    # awesome-openclaw
    awesome_data = fetch_awesome_openclaw()
    if awesome_data:
        report["sources"]["awesome-openclaw"] = awesome_data
    
    # ClawHub
    clawhub_data = fetch_clawhub_skills()
    if clawhub_data:
        report["sources"]["clawhub"] = clawhub_data
    
    # Hacker News
    hn_stories = fetch_hacker_news_ai()
    if hn_stories:
        report["sources"]["hacker-news"] = {
            "ai_stories": hn_stories,
            "count": len(hn_stories)
        }
    
    # 生成社区洞察
    print("  💡 生成社区洞察...")
    insights = []
    
    # 洞察 1: 生态系统规模
    if awesome_data and clawhub_data:
        insights.append({
            "type": "ecosystem",
            "title": "OpenClaw 生态系统持续扩张",
            "details": [
                f"awesome-openclaw: {awesome_data['total_resources']} 个资源，{awesome_data['category_count']} 个分类",
                f"ClawHub: {clawhub_data['stars']} stars, {clawhub_data['forks']} forks"
            ]
        })
    
    # 洞察 2: 社区热点
    if hn_stories:
        insights.append({
            "type": "trending",
            "title": f"Hacker News 发现 {len(hn_stories)} 个 AI 相关讨论",
            "stories": hn_stories[:5]
        })
    
    report["insights"] = insights
    
    # 保存报告
    output_file = OUTPUT_DIR / f"community-scraper-{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{output_file}")
    
    # 生成 Markdown 摘要
    md_summary = generate_markdown_summary(report)
    md_file = OUTPUT_DIR / f"community-scraper-{datetime.now().strftime('%Y%m%d')}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_summary)
    
    print(f"✅ Markdown 摘要已保存：{md_file}")
    
    return report

def generate_markdown_summary(report):
    """生成 Markdown 摘要"""
    md = ["# 社区趋势日报", ""]
    md.append(f"**生成时间**: {report['generated_at'][:19]}")
    md.append("")
    
    # awesome-openclaw
    if "awesome-openclaw" in report["sources"]:
        awesome = report["sources"]["awesome-openclaw"]
        md.append("## 📚 awesome-openclaw")
        md.append("")
        md.append(f"- 📦 资源总数：**{awesome['total_resources']}**")
        md.append(f"- 📂 分类数量：**{awesome['category_count']}**")
        md.append("")
        
        md.append("### 主要分类")
        for cat, resources in list(awesome['categories'].items())[:5]:
            md.append(f"- **{cat}**: {len(resources)} 个资源")
        md.append("")
    
    # ClawHub
    if "clawhub" in report["sources"]:
        clawhub = report["sources"]["clawhub"]
        md.append("## 🛠️  ClawHub 技能")
        md.append("")
        md.append(f"- ⭐ Stars: {clawhub['stars']}")
        md.append(f"- 🍴 Forks: {clawhub['forks']}")
        md.append(f"- 📄 {clawhub['description']}")
        md.append("")
    
    # Hacker News
    if "hacker-news" in report["sources"]:
        hn = report["sources"]["hacker-news"]
        md.append("## 📰 Hacker News AI 讨论")
        md.append("")
        md.append(f"发现 **{hn['count']}** 个 AI 相关讨论")
        md.append("")
        
        for i, story in enumerate(hn['ai_stories'][:5], 1):
            md.append(f"{i}. [{story['title']}]({story['hn_url']})")
            md.append(f"   - 👍 {story['score']} 分 | 💬 {story['comments']} 评论")
        md.append("")
    
    # 社区洞察
    if report["insights"]:
        md.append("## 💡 社区洞察")
        md.append("")
        
        for insight in report["insights"]:
            md.append(f"### {insight['title']}")
            if insight['type'] == 'ecosystem':
                for detail in insight['details']:
                    md.append(f"- {detail}")
            elif insight['type'] == 'trending':
                for story in insight['stories']:
                    md.append(f"- {story['title']}")
            md.append("")
    
    md.append("---")
    md.append("*自动生成于 Community Scraper*")
    
    return '\n'.join(md)

if __name__ == "__main__":
    report = generate_community_report()
    print("\n📊 社区抓取完成！")
    print(f"  - 发现 {len(report['insights'])} 条社区洞察")
    if "awesome-openclaw" in report["sources"]:
        print(f"  - awesome-openclaw: {report['sources']['awesome-openclaw']['total_resources']} 个资源")
    if "hacker-news" in report["sources"]:
        print(f"  - Hacker News: {report['sources']['hacker-news']['count']} 个 AI 讨论")
