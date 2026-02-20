#!/bin/bash
# Learning Upgrade - 月报入口脚本 v3.0
# 功能：编排每月复盘流程
# 调度：每月 1 日 10:00 (Asia/Shanghai)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/home/writer/.openclaw/workspace/logs/learning-upgrade"
DATE_STAMP=$(date +%Y%m%d)
ISO_DATE=$(date +%Y-%m-%d)
MONTH=$(date +%Y-%m)

# 加载环境变量
if [[ -f "/home/writer/.openclaw/.env" ]]; then
    set -a
    source /home/writer/.openclaw/.env
    set +a
fi

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_DIR/learning-monthly-${DATE_STAMP}.log"
}

main() {
    mkdir -p "$LOG_DIR"
    
    log "INFO" "=========================================="
    log "INFO" "Learning Upgrade 月报任务启动 (v3.0)"
    log "INFO" "日期：$ISO_DATE | 复盘上月"
    log "INFO" "=========================================="
    
    # 验证环境变量
    local missing=()
    [[ -z "${ARK_API_KEY:-}" ]] && missing+=("ARK_API_KEY")
    [[ -z "${MATON_API_KEY:-}" ]] && missing+=("MATON_API_KEY")
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log "ERROR" "缺少必需的环境变量：${missing[*]}"
        exit 1
    fi
    log "INFO" "环境变量验证通过 ✅"
    
    # 执行月报分析
    log "INFO" "执行月报分析脚本..."
    if python3 "$SCRIPT_DIR/monthly-reviewer.py" 2>&1 | tee -a "$LOG_DIR/learning-monthly-${DATE_STAMP}.log"; then
        log "INFO" "月报分析完成 ✅"
    else
        log "ERROR" "月报分析失败"
        exit 1
    fi
    
    log "INFO" "=========================================="
    log "INFO" "月报任务完成 ✅"
    log "INFO" "=========================================="
}

main "$@"
