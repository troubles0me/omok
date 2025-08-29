#!/bin/bash

# 빠른 재시작 스크립트 (Ubuntu 환경)

echo "🚀 빠른 재시작 시작..."

# 1. 모든 프로세스 종료
echo "🛑 기존 프로세스 종료 중..."
pkill -f "python.*llm_server" 2>/dev/null
pkill -f "python.*main" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null

# 2. 포트 강제 해제
echo "🔌 포트 정리 중..."
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null
sudo kill -9 $(sudo lsof -t -i:8001) 2>/dev/null
sudo kill -9 $(sudo lsof -t -i:5173) 2>/dev/null

# 3. 잠시 대기
sleep 2

# 4. 서버 재시작
echo "🔄 서버 재시작 중..."
cd /home/jme09042/omok
bash azure_start.sh
