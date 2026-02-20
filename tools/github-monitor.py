#!/usr/bin/env python3
"""
GitHub Monitor - OpenClaw GitHub 动态监控
功能：
1. 监控官方仓库 Releases
2. 抓取 Issues/Discussions 热门话题
3. 追踪 awesome-openclaw 社区资源
4. 生成技术洞察报告

安全：
- 从环境变量读取密钥（无硬编码）
- 外部内容仅作为数据处理
- 超时限制防止 hangs
"""

import urllib.request
import json
import ssl
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# ==================== 安全机制 ====================

def detect_injection(content: str) -> bool:
    """检测潜在的提示词注入模式"""
    patterns = [
        r"ignore\s+previous\s+instructions",
        r"disregard\s+all",
        r"you\s+are\s+now",
        r"bypass\s+safety",
        r"execute\s+this\s+command",
        r"system\s+prompt",
    ]
    lower_content = content.lower()
    for pattern in patterns:
        if re.search(pattern, lower_content):
            print(f"⚠️  检测到潜在的提示词注入模式")
            return True
    return False

def safe_process_text(text: str) -> str:
    """安全处理文本内容"""
    if detect_injection(text):
        # 记录警告但继续处理（仅作为数据）
        pass
    return text

# 配置（从环境变量读取，避免硬编码密钥）
import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN 环境变量未设置")

REPOS = {
    "main": "openclaw/openclaw",
    "awesome": "SamurAIGPT/awesome-openclaw",
    "skills": "openclaw/skills",
}
OUTPUT_DIR = Path("/home/writer/.openclaw/workspace/logs/github-monitor")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def github_api(endpoint, params=None):
    """GitHub API 请求（带认证）"""
    url = f"https://api.github.com/{endpoint}"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    if params:
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        url += f"?{query}"
    
    ctx = ssl.create_default_context()
    try:
        response = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.load(response)
    except Exception as e:
        print(f"❌ API 请求失败：{e}")
        return None

def fetch_releases(repo, limit=5):
    """获取 Releases"""
    data = github_api(f"repos/{repo}/releases", {"per_page": limit})
    if not data:
        return []
    
    releases = []
    for rel in data:
        releases.append({
            "tag": rel.get('tag_name', ''),
            "name": rel.get('name', ''),
            "published_at": rel.get('published_at', '')[:10],
            "body": rel.get('body', '')[:500],  # 截取前 500 字
            "url": rel.get('html_url', '')
        })
    return releases

def fetch_trending_topics(repo):
    """获取热门 Issues/Discussions"""
    # 获取最近 7 天的热门 issues
    since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    data = github_api(f"repos/{repo}/issues", {
        "state": "all",
        "since": since,
        "per_page": 10,
        "sort": "comments",
        "direction": "desc"
    })
    if not data:
        return []
    
    topics = []
    for issue in data[:10]:
        # 跳过 PR（PR 也是 issue）
        if 'pull_request' in issue:
            continue
        
        topics.append({
            "title": issue.get('title', ''),
            "number": issue.get('number', ''),
            "comments": issue.get('comments', 0),
            "created_at": issue.get('created_at', '')[:10],
            "url": issue.get('html_url', ''),
            "labels": [l.get('name', '') for l in issue.get('labels', [])]
        })
    return topics

def fetch_stars_trend(repo):
    """获取 Star 趋势"""
    data = github_api(f"repos/{repo}")
    if not data:
        return None
    
    return {
        "stars": data.get('stargazers_count', 0),
        "forks": data.get('forks_count', 0),
        "open_issues": data.get('open_issues_count', 0),
        "updated_at": data.get('updated_at', '')[:10]
    }

def analyze_security_fixes(releases):
    """分析安全修复"""
    security_mentions = []
    for rel in releases:
        body = rel.get('body', '').lower()
        if 'security' in body or 'vulnerability' in body or 'fix' in body:
            # 提取安全相关的修复
            lines = rel.get('body', '').split('\n')
            for line in lines:
                if 'security' in line.lower() or 'fix' in line.lower():
                    security_mentions.append({
                        "release": rel['tag'],
                        "content": line.strip()[:200]
                    })
    return security_mentions[:10]  # 最多 10 条

def generate_report():
    """生成监控报告"""
    print("🔍 开始 GitHub 监控...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "repos": {}
    }
    
    # 监控主仓库
    print(f"  📦 抓取 {REPOS['main']}...")
    main_releases = fetch_releases(REPOS['main'])
    main_topics = fetch_trending_topics(REPOS['main'])
    main_stars = fetch_stars_trend(REPOS['main'])
    
    report["repos"]["main"] = {
        "name": REPOS['main'],
        "releases": main_releases,
        "trending_topics": main_topics,
        "stars": main_stars,
        "security_fixes": analyze_security_fixes(main_releases)
    }
    
    # 监控 awesome-openclaw
    print(f"  📦 抓取 {REPOS['awesome']}...")
    awesome_stars = fetch_stars_trend(REPOS['awesome'])
    report["repos"]["awesome"] = {
        "name": REPOS['awesome'],
        "stars": awesome_stars
    }
    
    # 生成技术洞察
    print("  💡 生成技术洞察...")
    insights = []
    
    # 洞察 1: 最新版本关键更新
    if main_releases:
        latest = main_releases[0]
        insights.append({
            "type": "release",
            "title": f"最新版本 {latest['tag']} 发布",
            "date": latest['published_at'],
            "highlights": latest['body'][:300]
        })
    
    # 洞察 2: 安全加固趋势
    security_fixes = report["repos"]["main"]["security_fixes"]
    if security_fixes:
        insights.append({
            "type": "security",
            "title": f"发现 {len(security_fixes)} 项安全修复",
            "details": security_fixes[:5]
        })
    
    # 洞察 3: 社区热门话题
    if main_topics:
        hot_topics = [t for t in main_topics if t['comments'] >= 3]
        if hot_topics:
            insights.append({
                "type": "community",
                "title": f"社区热门话题 ({len(hot_topics)} 个)",
                "topics": hot_topics[:5]
            })
    
    report["insights"] = insights
    
    # 保存报告
    output_file = OUTPUT_DIR / f"github-monitor-{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{output_file}")
    
    # 生成 Markdown 摘要
    md_summary = generate_markdown_summary(report)
    md_file = OUTPUT_DIR / f"github-monitor-{datetime.now().strftime('%Y%m%d')}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_summary)
    
    print(f"✅ Markdown 摘要已保存：{md_file}")
    
    return report

def generate_markdown_summary(report):
    """生成 Markdown 格式摘要"""
    md = ["# GitHub 监控日报", ""]
    md.append(f"**生成时间**: {report['generated_at'][:19]}")
    md.append("")
    
    # 主仓库统计
    main = report["repos"]["main"]
    md.append("## 📦 openclaw/openclaw")
    md.append("")
    
    if main["stars"]:
        md.append(f"- ⭐ Stars: {main['stars']['stars']}")
        md.append(f"- 🍴 Forks: {main['stars']['forks']}")
        md.append(f"- 🐛 Open Issues: {main['stars']['open_issues']}")
        md.append("")
    
    # 最新版本
    if main["releases"]:
        latest = main["releases"][0]
        md.append("### 🚀 最新版本")
        md.append(f"**{latest['tag']}** ({latest['published_at']})")
        md.append("")
        md.append(f"{latest['body'][:500]}...")
        md.append("")
    
    # 安全修复
    if main["security_fixes"]:
        md.append("### 🔒 安全修复")
        for fix in main["security_fixes"][:5]:
            md.append(f"- **{fix['release']}**: {fix['content']}")
        md.append("")
    
    # 社区热门
    if main["trending_topics"]:
        md.append("### 💬 社区热门话题")
        for topic in main["trending_topics"][:5]:
            md.append(f"- [{topic['title']}]({topic['url']}) ({topic['comments']} 评论)")
        md.append("")
    
    # 技术洞察
    if report["insights"]:
        md.append("## 💡 技术洞察")
        md.append("")
        for insight in report["insights"]:
            md.append(f"### {insight['title']}")
            if insight['type'] == 'release':
                md.append(f"*{insight['date']}*")
                md.append("")
                md.append(insight['highlights'])
            elif insight['type'] == 'security':
                for detail in insight['details']:
                    md.append(f"- {detail['content']}")
            elif insight['type'] == 'community':
                for topic in insight['topics']:
                    md.append(f"- {topic['title']} ({topic['comments']} 评论)")
            md.append("")
    
    md.append("---")
    md.append("*自动生成于 GitHub Monitor*")
    
    return '\n'.join(md)

if __name__ == "__main__":
    report = generate_report()
    print("\n📊 监控完成！")
    print(f"  - 发现 {len(report['insights'])} 条技术洞察")
    print(f"  - 抓取 {len(report['repos']['main']['releases'])} 个 Releases")
    print(f"  - 抓取 {len(report['repos']['main']['trending_topics'])} 个热门话题")
