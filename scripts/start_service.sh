#!/bin/bash
# 启动股票异动分析服务

APP_DIR="/opt/stock-swing-calcu"
SRC_DIR="$APP_DIR/src"
LOG_FILE="$APP_DIR/logs/service.log"
PID_FILE="$APP_DIR/logs/service.pid"
STOCK_FILE="$APP_DIR/data/stock_may.csv"

# 创建日志目录
mkdir -p "$APP_DIR/logs"

# 检查是否已运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "服务已在运行 (PID: $PID)"
        exit 0
    else
        # PID文件存在但进程不存在，删除PID文件
        rm "$PID_FILE"
    fi
fi

# 激活虚拟环境（如果使用）
# source "$APP_DIR/venv/bin/activate"

echo "启动股票异动分析服务..."

# 后台启动服务
cd "$SRC_DIR"
nohup python web_app.py --file "$STOCK_FILE" > "$LOG_FILE" 2>&1 &

# 保存PID
echo $! > "$PID_FILE"

echo "服务启动成功 (PID: $!)"
echo "日志文件: $LOG_FILE"
echo "服务端口: 5000"