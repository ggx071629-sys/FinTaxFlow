#!/bin/bash
# Finder double-click shortcut. Keep this file at the repo root.
cd "$(dirname "$0")" || exit 1
./start.sh "$@"
status=$?
if [ "$status" -ne 0 ]; then
  echo
  echo "启动失败（退出码 ${status}）。"
  read -r -p "按回车关闭窗口..."
fi
exit "$status"
