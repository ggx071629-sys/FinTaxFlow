#!/usr/bin/env bash
# Shared local lifecycle helpers, compatible with macOS Bash 3.2.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.docker/bin"
RUN_DIR="$ROOT/var/run"
LOG_DIR="$ROOT/var/logs"
log() { printf '%s\n' "$*"; }
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@"
  else
    fail "未找到 Docker Compose，请安装 Docker Desktop"
  fi
}
alive() { [[ "${1:-}" =~ ^[1-9][0-9]*$ ]] && kill -0 "$1" 2>/dev/null; }
process_stamp() { LC_ALL=C TZ=UTC0 ps -p "$1" -o lstart= 2>/dev/null; }
port_pid() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | sort -u || true; }

# Only recognize this checkout's Node/UniApp H5 server, never just its port.
project_h5_pid() {
  local pid="$1" process_dir executable command_line
  alive "$pid" || return 1
  process_dir="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  [[ "$process_dir" == "$ROOT/frontend" ]] || return 1
  executable="$(ps -ww -p "$pid" -o comm= 2>/dev/null)" || return 1
  [[ "${executable##*/}" == node ]] || return 1
  command_line="$(ps -ww -p "$pid" -o command= 2>/dev/null)" || return 1
  case "$command_line" in
    *" $ROOT/frontend/node_modules/.bin/uni "*) return 0 ;;
    *) return 1 ;;
  esac
}

project_api_pid() {
  local pid="$1" process_dir executable command_line
  alive "$pid" || return 1
  process_dir="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  [[ "$process_dir" == "$ROOT/backend" ]] || return 1
  executable="$(ps -ww -p "$pid" -o comm= 2>/dev/null)" || return 1
  case "${executable##*/}" in Python*|python*) ;; *) return 1 ;; esac
  command_line="$(ps -ww -p "$pid" -o command= 2>/dev/null)" || return 1
  case "$command_line" in
    *" $ROOT/backend/.venv/bin/uvicorn app.main:app "*) return 0 ;;
    *) return 1 ;;
  esac
}

# Ascend only a verified service's ancestors; do not search/kill arbitrary Bash.
launcher_of() {
  local pid="$1" command_line executable i
  for ((i=0; i<6; i++)); do
    alive "$pid" || return 1
    command_line="$(ps -ww -p "$pid" -o command= 2>/dev/null)" || return 1
    executable="$(ps -ww -p "$pid" -o comm= 2>/dev/null)" || return 1
    if [[ "${executable##*/}" == bash ]]; then
      case "$command_line" in
        *" $ROOT/scripts/start.sh"|*" $ROOT/scripts/start.sh "*) printf '%s\n' "$pid"; return 0 ;;
      esac
    fi
    pid="$(ps -p "$pid" -o ppid= 2>/dev/null)" || return 1
    pid="${pid//[[:space:]]/}"
  done
  return 1
}

# Repair missing/old-locale records only from verified local listeners.
# Never called by --check.
recover_runtime_records() {
  local api_pid h5_pid api_launcher='' h5_launcher='' launcher=''
  api_pid="$(port_pid 8000)"
  h5_pid="$(port_pid 5173)"
  if project_api_pid "$api_pid"; then
    mkdir -p "$RUN_DIR"
    owned_pid "$RUN_DIR/backend.pid" >/dev/null || record_pid "$api_pid" "$RUN_DIR/backend.pid"
    api_launcher="$(launcher_of "$api_pid" || true)"
  fi
  if project_h5_pid "$h5_pid"; then
    mkdir -p "$RUN_DIR"
    owned_pid "$RUN_DIR/frontend.pid" >/dev/null || record_pid "$h5_pid" "$RUN_DIR/frontend.pid"
    h5_launcher="$(launcher_of "$h5_pid" || true)"
  fi
  if [[ -n "$api_launcher" && -n "$h5_launcher" && "$api_launcher" != "$h5_launcher" ]]; then
    return 0
  fi
  launcher="${api_launcher:-$h5_launcher}"
  if [[ -n "$launcher" ]]; then
    owned_pid "$RUN_DIR/launcher.pid" >/dev/null || record_pid "$launcher" "$RUN_DIR/launcher.pid"
  fi
}

# A timestamp prevents stale records from stopping recycled PIDs.
record_pid() {
  local pid="$1" file="$2" stamp
  stamp="$(process_stamp "$pid")" || return 1
  [[ -n "$stamp" ]] || return 1
  printf '%s\n%s\n' "$pid" "$stamp" >"$file"
}
owned_pid() {
  local file="$1" pid stamp current
  [[ -f "$file" ]] || return 1
  { IFS= read -r pid; IFS= read -r stamp; } <"$file" || return 1
  alive "$pid" || return 1
  current="$(process_stamp "$pid")" || return 1
  [[ -n "$stamp" && "$current" == "$stamp" ]] || return 1
  printf '%s\n' "$pid"
}
stop_tree() {
  local pid="$1" child i
  alive "$pid" || return 0
  # npm -> shell -> node can be more than one generation deep.
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do stop_tree "$child"; done
  kill "$pid" 2>/dev/null || true
  for i in 1 2 3 4 5 6 7 8 9 10; do
    alive "$pid" || return 0
    sleep 0.2
  done
  kill -9 "$pid" 2>/dev/null || true
}
stop_recorded() {
  local file="$1" label="$2" pid
  if pid="$(owned_pid "$file")"; then
    stop_tree "$pid"
    log "已停止 ${label}（pid ${pid}）"
  elif [[ -f "$file" ]]; then
    log "$label 的进程记录已过期或来自旧版脚本，未向该 PID 发送信号。"
  fi
  rm -f "$file"
}
