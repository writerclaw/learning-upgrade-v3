#!/bin/bash
# Learning Upgrade - 周报入口脚本 v3.0
# 功能：编排每周复盘流程
# 调度：每周一 09:00 (Asia/Shanghai)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/home/writer/.openclaw/workspace/logs/learning-upgrade"
DATE_STAMP=$(date +%Y%m%d)
ISO_DATE=$(date +%Y-%m-%d)
WEEK_NUM=$(date +%V)

# 加载环境变量
if [[ -f "/home/writer/.openclaw/.env" ]]; then
    set -a
    source /home/writer/.openclaw/.env
    set +a
fi

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_DIR/learning-weekly-${DATE_STAMP}.log"
}

main() {
    mkdir -p "$LOG_DIR"
    
    log "INFO" "=========================================="
    log "INFO" "Learning Upgrade 周报任务启动 (v3.0)"
    log "INFO" "日期：$ISO_DATE | 周：W${WEEK_NUM}"
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
    
    # 执行周报分析
    log "INFO" "执行周报分析脚本..."
    if python3 "$SCRIPT_DIR/weekly-reviewer.py" 2>&1 | tee -a "$LOG_DIR/learning-weekly-${DATE_STAMP}.log"; then
        log "INFO" "周报分析完成 ✅"
    else
        log "ERROR" "周报分析失败"
        exit 1
    fi
    
    log "INFO" "=========================================="
    log "INFO" "周报任务完成 ✅"
    log "INFO" "=========================================="
}

main "$@"
