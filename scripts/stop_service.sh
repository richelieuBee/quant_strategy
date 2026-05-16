#!/bin/bash
# 停止股票异动分析服务

APP_DIR="/opt/stock-swing-calcu"
PID_FILE="$APP_DIR/logs/service.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "服务未运行（未找到PID文件）"
    exit 0
fi

PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! kill -0 "$PID" 2>/dev/null; then
    echo "服务进程不存在，清理PID文件"
    rm "$PID_FILE"
    exit 0
fi

echo "正在停止服务 (PID: $PID)..."

# 优雅停止服务
kill "$PID"

# 等待进程结束
for i in {1..30}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "服务已成功停止"
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果进程仍未结束，强制终止
echo "强制终止服务..."
kill -9 "$PID"
rm "$PID_FILE"
echo "服务已强制停止"