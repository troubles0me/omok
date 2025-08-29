#!/bin/bash

# 서버 재시작 스크립트

echo "🔄 Omok 게임 서버 재시작 중..."
echo "================================"

# 기존 서버 프로세스 종료
echo "🛑 기존 서버 프로세스 종료 중..."

# LLM 서버 종료
pkill -f "python.*llm_server" 2>/dev/null
echo "   🤖 LLM 서버 종료됨"

# 백엔드 서버 종료
pkill -f "python.*main" 2>/dev/null
echo "   🔧 백엔드 서버 종료됨"

# 프론트엔드 서버 종료
pkill -f "npm.*dev" 2>/dev/null
echo "   🌐 프론트엔드 서버 종료됨"

# 잠시 대기
sleep 2

echo ""
echo "🚀 서버 재시작 중..."
echo ""

# azure_start.sh 실행
./azure_start.sh
