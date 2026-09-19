#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/runtime.sh"
cd "$ROOT"
CHECK_ONLY=0
OPEN_BROWSER=1
INSTALL_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --no-open) OPEN_BROWSER=0 ;;
    --install-deps) INSTALL_DEPS=1 ;;
    -h|--help)
      cat <<'HELP'
用法：./start.sh [--check] [--no-open] [--install-deps]
  --check         只检查本地环境、配置与端口；不安装依赖或启动服务
  --no-open       启动后不自动打开浏览器
  --install-deps  强制重新安装前后端依赖
默认：按需安装依赖，迁移并初始化数据库，前台运行 API + H5。
停止：Ctrl+C 或 npm stop；停止数据库：npm run stop:all（保留数据卷）。
HELP
      exit 0 ;;
    *) fail "未知参数：${arg}；使用 ./start.sh --help 查看用法" ;;
  esac
done
API_URL="http://127.0.0.1:8000/api/health"
APP_URL="http://127.0.0.1:5173"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
# Finder does not load the interactive shell's nvm setup.
if ! command -v node >/dev/null 2>&1 && [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]]; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  source "$NVM_DIR/nvm.sh" --no-use
  nvm use --silent default || fail "请为 nvm 配置可用的 default Node.js 版本"
fi
http_ok() { curl -fsS -o /dev/null --max-time 2 "$1" >/dev/null 2>&1; }
open_app() {
  if [[ "$OPEN_BROWSER" -eq 1 ]] && command -v open >/dev/null 2>&1; then
    open "$APP_URL" || log "浏览器未能自动打开，请手动访问 $APP_URL"
  fi
}
pick_python() {
  local candidate
  for candidate in "$ROOT/backend/.venv/bin/python" python3.12 /opt/homebrew/bin/python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' 2>/dev/null; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}
log "检查本地运行环境…"
for command_name in docker node npm curl lsof ps pgrep cksum; do
  command -v "$command_name" >/dev/null 2>&1 || fail "未找到 ${command_name}，请参照 README 安装依赖"
done
ps -p $$ -o pid= >/dev/null || fail "无法读取进程信息，请在本机终端运行"
PYTHON="$(pick_python)" || fail "需要 Python 3.12+"
docker info >/dev/null 2>&1 || fail "无法连接 Docker，请启动 Docker Desktop 并确认当前终端有访问权限"
compose config --quiet
log "  Node $(node --version) / npm $(npm --version) / $("$PYTHON" --version)"
for config_file in backend/.env frontend/.env.local; do
  if [[ -f "$ROOT/$config_file" ]]; then
    log "  保留现有配置：$config_file"
  else
    log "  启动时将从示例创建：$config_file"
  fi
done
if [[ "$(uname -s)" == Darwin && ! -x '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' && ! -x "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
  log "  提示：未在 Applications 中发现 Chrome；默认模拟申报需要本机 Chrome。"
fi
managed=0
legacy_frontend=''
if owned_pid "$RUN_DIR/launcher.pid" >/dev/null && owned_pid "$RUN_DIR/backend.pid" >/dev/null && owned_pid "$RUN_DIR/frontend.pid" >/dev/null && http_ok "$API_URL" && http_ok "$APP_URL"; then
  managed=1
fi
if [[ "$managed" -eq 0 ]] && project_api_pid "$(port_pid 8000)" && project_h5_pid "$(port_pid 5173)" && http_ok "$API_URL" && http_ok "$APP_URL"; then
  managed=1
fi
if [[ "$managed" -eq 0 ]] && owned_pid "$RUN_DIR/launcher.pid" >/dev/null; then
  fail "已有启动会话正在准备或退出，请查看原启动终端或执行 npm stop 后重试"
fi
for port in 8000 5173; do
  listener="$(port_pid "$port")"
  if [[ -n "$listener" && "$managed" -eq 0 ]]; then
    if [[ "$port" -eq 5173 ]] && project_h5_pid "$listener"; then
      legacy_frontend="$listener"
      log "  发现本项目单独运行的 H5（pid ${listener}），正式启动时将重启并统一管理。"
    else
      fail "端口 $port 已被进程 $listener 占用；本项目服务可先执行 npm stop，其他服务请在原终端停止后重试"
    fi
  fi
done
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  log "环境检查通过；尚未验证依赖完整性、数据库连接、迁移或模拟申报。"
  exit 0
fi
if [[ "$managed" -eq 1 ]]; then
  [[ "$INSTALL_DEPS" -eq 0 ]] || fail "请先停止项目，再使用 --install-deps"
  recover_runtime_records
  log "项目已在运行：$APP_URL"
  open_app
  exit 0
fi
mkdir -p "$RUN_DIR" "$LOG_DIR"
if ! mkdir "$RUN_DIR/start.lock" 2>/dev/null; then
  fail "已有启动会话或遗留锁；先执行 npm stop。若刚中断了初始化，确认原终端已退出后移除 var/run/start.lock 空目录再启动"
fi
backend_pid=''
frontend_pid=''
cleanup() {
  trap - EXIT INT TERM HUP
  [[ -z "$frontend_pid" ]] || stop_tree "$frontend_pid"
  [[ -z "$backend_pid" ]] || stop_tree "$backend_pid"
  rm -f "$RUN_DIR/launcher.pid" "$RUN_DIR/backend.pid" "$RUN_DIR/frontend.pid"
  rmdir "$RUN_DIR/start.lock" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM HUP
record_pid $$ "$RUN_DIR/launcher.pid" || fail "无法记录启动进程"
if [[ -n "$legacy_frontend" ]]; then
  # Revalidate after taking the startup lock, before sending any signal.
  listener="$(port_pid 5173)"
  if [[ -n "$listener" ]]; then
    [[ "$listener" == "$legacy_frontend" ]] && project_h5_pid "$listener" || fail "5173 端口进程已变化，请重新启动"
    log "重启本项目遗留 H5（pid ${listener}）…"
    stop_tree "$listener"
    [[ -z "$(port_pid 5173)" ]] || fail "5173 端口尚未释放，请稍后重试"
  fi
fi
log "1/4 启动 PostgreSQL…"
compose up -d postgres
ready=0
for ((i=0; i<60; i++)); do
  if compose exec -T postgres pg_isready -U fintax -d fintaxflow >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[[ "$ready" -eq 1 ]] || fail "PostgreSQL 未能就绪，请运行 docker compose logs postgres"
log "2/4 准备后端…"
cd "$ROOT/backend"
if [[ ! -x .venv/bin/python ]]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' || fail "backend/.venv 需要 Python 3.12+，请移走旧虚拟环境后重试"
backend_stamp="$(cksum < pyproject.toml)"
if [[ "$INSTALL_DEPS" -eq 1 || ! -f .venv/.fintax-deps || "$(cat .venv/.fintax-deps)" != "$backend_stamp" ]] || ! .venv/bin/python -m pip check >/dev/null 2>&1; then
  .venv/bin/python -m pip install -e .
  .venv/bin/python -m pip check
  printf '%s\n' "$backend_stamp" > .venv/.fintax-deps
else
  log "  后端依赖未变化，跳过安装。"
fi
[[ -f .env ]] || cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
log "3/4 准备前端…"
cd "$ROOT/frontend"
frontend_stamp="$(cat package.json package-lock.json | cksum)"
if [[ "$INSTALL_DEPS" -eq 1 || ! -x node_modules/.bin/uni || ! -f node_modules/.fintax-deps || "$(cat node_modules/.fintax-deps)" != "$frontend_stamp" ]]; then
  npm ci
  printf '%s\n' "$frontend_stamp" > node_modules/.fintax-deps
else
  log "  前端依赖未变化，跳过安装。"
fi
[[ -f .env.local ]] || cp .env.example .env.local
log "4/4 启动 API 与 H5 开发服务…"
printf '\n--- %s ---\n' "$(date '+%Y-%m-%d %H:%M:%S')" >>"$BACKEND_LOG"
printf '\n--- %s ---\n' "$(date '+%Y-%m-%d %H:%M:%S')" >>"$FRONTEND_LOG"
(cd "$ROOT/backend"; exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) >>"$BACKEND_LOG" 2>&1 &
backend_pid=$!
record_pid "$backend_pid" "$RUN_DIR/backend.pid" || fail "后端启动失败，查看 $BACKEND_LOG"
(cd "$ROOT/frontend"; exec npm run dev:h5) >>"$FRONTEND_LOG" 2>&1 &
frontend_pid=$!
record_pid "$frontend_pid" "$RUN_DIR/frontend.pid" || fail "前端启动失败，查看 $FRONTEND_LOG"
ready=0
for ((i=0; i<60; i++)); do
  alive "$backend_pid" || fail "后端已退出，查看 $BACKEND_LOG"
  alive "$frontend_pid" || fail "前端已退出，查看 $FRONTEND_LOG"
  if http_ok "$API_URL" && http_ok "$APP_URL"; then ready=1; break; fi
  sleep 1
done
[[ "$ready" -eq 1 ]] || fail "服务就绪检查超时，查看 $LOG_DIR"
log "
FinTaxFlow 已启动（保持此终端打开，Ctrl+C 停止）
  H5    $APP_URL
  文档  http://127.0.0.1:8000/docs
  日志  $LOG_DIR
  账号  demo_boss01 / demo_boss02，密码均为 123456
"
open_app
while alive "$backend_pid" && alive "$frontend_pid"; do sleep 1; done
fail "前端或后端意外退出，正在清理本次服务；查看 $LOG_DIR"
