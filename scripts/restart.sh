#!/bin/bash
# 重启股票异动分析服务并检查状态

./stop_service.sh
./start_service.sh
./status_service.sh