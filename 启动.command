#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python launch.py
elif command -v python3 >/dev/null 2>&1; then
  python3 launch.py
else
  print '需要先安装 Python 3.10 或更新版本。'
fi
read '?按回车关闭窗口'
