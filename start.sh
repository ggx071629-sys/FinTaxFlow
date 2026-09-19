#!/usr/bin/env bash
# Root shortcut: start the whole FinTaxFlow stack.
exec "$(cd "$(dirname "$0")" && pwd)/scripts/start.sh" "$@"
