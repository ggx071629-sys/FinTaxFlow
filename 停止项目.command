#!/bin/bash
cd "$(dirname "$0")" || exit 1
./scripts/stop.sh "$@"
status=$?
echo
read -r -p "按回车关闭窗口..."
exit "$status"
