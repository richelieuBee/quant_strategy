#!/bin/bash
# 检查股票异动分析服务状态

APP_DIR="/opt/stock-swing-calcu"
PID_FILE="$APP_DIR/logs/service.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "服务未运行"
    exit 3
fi

PID=$(cat "$PID_FILE")

# 检查进程是否存在
if kill -0 "$PID" 2>/dev/null; then
    echo "服务运行中 (PID: $PID)"
    exit 0
else
    echo "服务已停止（PID文件存在但进程不存在）"
    exit 1
fi