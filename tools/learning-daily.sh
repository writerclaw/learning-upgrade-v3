#!/bin/bash
# Learning Upgrade - 主入口脚本 v3.0
# 功能：执行每日学习流程（4 步 + 行动项追踪）
# 变更：在 tech-analyzer 完成后自动提取行动项

set -euo pipefail

# ==================== 配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="/home/writer/.openclaw/workspace"
LOG_DIR="$WORKSPACE_DIR/logs/learning-upgrade"
DIGEST_DIR="$WORKSPACE_DIR/logs/daily-digest"
DATE_STAMP=$(date +%Y%m%d)
ISO_DATE=$(date +%Y-%m-%d)

# 加载环境变量
if [[ -f "/home/writer/.openclaw/.env" ]]; then
    set -a
    source /home/writer/.openclaw/.env
    set +a
fi

# ==================== 安全机制 ====================

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_DIR/learning-daily-${DATE_STAMP}.log"
}

error_exit() {
    log "ERROR" "$1"
    exit 1
}

verify_env() {
    log "INFO" "验证环境变量..."
    
    local missing=()
    
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        missing+=("GITHUB_TOKEN")
    fi
    
    if [[ -z "${MATON_API_KEY:-}" ]]; then
        missing+=("MATON_API_KEY")
    fi
    
    if [[ -z "${ARK_API_KEY:-}" ]]; then
        missing+=("ARK_API_KEY")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error_exit "缺少必需的环境变量：${missing[*]}"
    fi
    
    log "INFO" "环境变量验证通过 ✅"
}

detect_injection() {
    local content="$1"
    local patterns=(
        "ignore previous instructions"
        "disregard all"
        "you are now"
        "bypass safety"
        "execute this command"
        "run this code"
        "system prompt"
        "override your"
    )
    
    local lower_content=$(echo "$content" | tr '[:upper:]' '[:lower:]')
    
    for pattern in "${patterns[@]}"; do
        if [[ "$lower_content" == *"$pattern"* ]]; then
            log "WARN" "检测到潜在的提示词注入模式：$pattern"
            return 1
        fi
    done
    
    return 0
}

safe_exec_python() {
    local script="$1"
    
    if [[ ! -f "$script" ]]; then
        error_exit "脚本不存在：$script"
    fi
    
    log "INFO" "执行：$script"
    
    local output
    if ! output=$(python3 "$script" 2>&1); then
        log "ERROR" "脚本执行失败：$output"
        return 1
    fi
    
    if ! detect_injection "$output"; then
        log "WARN" "输出包含可疑内容，已过滤"
    fi
    
    echo "$output"
    log "INFO" "执行完成 ✅"
    return 0
}

# ==================== 生成日报汇总 ====================

generate_daily_digest() {
    log "INFO" "生成日报汇总..."
    
    mkdir -p "$DIGEST_DIR"
    
    local digest_file="$DIGEST_DIR/${DATE_STAMP}.md"
    
    cat > "$digest_file" << EOF
# 📅 ${ISO_DATE} 学习日报汇总

**生成时间**: $(date '+%Y-%m-%d %H:%M')

## 报告来源

EOF
    
    # 合并 GitHub 报告
    local gh_file="$WORKSPACE_DIR/logs/github-monitor/github-monitor-${DATE_STAMP}.md"
    if [[ -f "$gh_file" ]]; then
        echo "### GitHub 监控" >> "$digest_file"
        echo "" >> "$digest_file"
        head -50 "$gh_file" >> "$digest_file"
        echo "" >> "$digest_file"
        echo "---" >> "$digest_file"
        echo "" >> "$digest_file"
    fi
    
    # 合并社区报告
    local comm_file="$WORKSPACE_DIR/logs/community-scraper/community-scraper-${DATE_STAMP}.md"
    if [[ -f "$comm_file" ]]; then
        echo "### 社区趋势" >> "$digest_file"
        echo "" >> "$digest_file"
        head -50 "$comm_file" >> "$digest_file"
        echo "" >> "$digest_file"
        echo "---" >> "$digest_file"
        echo "" >> "$digest_file"
    fi
    
    # 合并技术分析
    local tech_file="$WORKSPACE_DIR/logs/tech-analyzer/tech-analysis-${DATE_STAMP}.md"
    if [[ -f "$tech_file" ]]; then
        echo "### 技术深度分析" >> "$digest_file"
        echo "" >> "$digest_file"
        head -80 "$tech_file" >> "$digest_file"
        echo "" >> "$digest_file"
    fi
    
    echo "---" >> "$digest_file"
    echo "*自动汇总于 $(date '+%H:%M')*" >> "$digest_file"
    
    log "INFO" "日报汇总已保存: $digest_file"
}

# ==================== 主流程 ====================

main() {
    log "INFO" "=========================================="
    log "INFO" "Learning Upgrade 学习改进任务启动 (v3.0)"
    log "INFO" "日期：$ISO_DATE"
    log "INFO" "=========================================="
    
    mkdir -p "$LOG_DIR"
    
    # 1. 验证环境
    verify_env
    
    # 2. GitHub 监控
    log "INFO" "步骤 1/5: GitHub 监控..."
    safe_exec_python "$SCRIPT_DIR/github-monitor.py" || log "WARN" "GitHub 监控部分失败"
    
    # 3. 社区抓取
    log "INFO" "步骤 2/5: 社区抓取..."
    safe_exec_python "$SCRIPT_DIR/community-scraper.py" || log "WARN" "社区抓取部分失败"
    
    # 4. 技术分析（v3.0 增强: 输出包含行动项）
    log "INFO" "步骤 3/5: 技术深度分析..."
    safe_exec_python "$SCRIPT_DIR/tech-analyzer.py" || log "WARN" "技术分析部分失败"
    
    # 5. Notion 日记
    log "INFO" "步骤 4/5: 更新 Notion 学习日记..."
    safe_exec_python "$SCRIPT_DIR/notion-updater.py" || log "WARN" "Notion 更新部分失败"
    
    # 6. 生成日报汇总 (v3.0 新增)
    log "INFO" "步骤 5/5: 生成日报汇总..."
    generate_daily_digest || log "WARN" "日报汇总生成失败"
    
    log "INFO" "=========================================="
    log "INFO" "学习改进任务完成 ✅ (v3.0)"
    log "INFO" "输出文件:"
    log "INFO" "  - $WORKSPACE_DIR/logs/github-monitor/github-monitor-${DATE_STAMP}.md"
    log "INFO" "  - $WORKSPACE_DIR/logs/community-scraper/community-scraper-${DATE_STAMP}.md"
    log "INFO" "  - $WORKSPACE_DIR/logs/tech-analyzer/tech-analysis-${DATE_STAMP}.md"
    log "INFO" "  - $DIGEST_DIR/${DATE_STAMP}.md (汇总)"
    log "INFO" "  - Notion: ${ISO_DATE} 学习日报"
    log "INFO" "=========================================="
}

main "$@"
