#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/runtime.sh"
STOP_DOCKER=0
for arg in "$@"; do
  case "$arg" in
    --all) STOP_DOCKER=1 ;;
    -h|--help) log '用法：./scripts/stop.sh [--all]（--all 同时停止数据库，保留数据卷）'; exit 0 ;;
    *) fail "未知参数：$arg" ;;
  esac
done
for command_name in pgrep lsof; do
  command -v "$command_name" >/dev/null 2>&1 || fail "未找到 ${command_name}，无法安全清理子进程"
done
ps -p $$ -o pid= >/dev/null || fail "无法读取进程信息，请在本机终端运行"
recover_runtime_records
# The foreground supervisor cleans up its own children first.
if launcher_pid="$(owned_pid "$RUN_DIR/launcher.pid")"; then
  kill -TERM "$launcher_pid"
  for ((i=0; i<50; i++)); do
    owned_pid "$RUN_DIR/launcher.pid" >/dev/null || break
    sleep 0.2
  done
  if owned_pid "$RUN_DIR/launcher.pid" >/dev/null; then
    fail "启动终端仍在退出，请等待初始化命令结束后重试"
  fi
fi
stop_recorded "$RUN_DIR/frontend.pid" '前端'
stop_recorded "$RUN_DIR/backend.pid" '后端'
rm -f "$RUN_DIR/launcher.pid"
if [[ "$STOP_DOCKER" -eq 1 ]]; then
  compose stop postgres
  log '已停止 PostgreSQL 容器（保留数据卷）。'
fi
log '停止完成；无法确认归属的其他服务请在原启动终端关闭。'
