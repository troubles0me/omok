#!/bin/bash

# 간단한 백그라운드 실행 스크립트

echo "🚀 간단한 백그라운드 실행 시작..."

# 프로젝트 루트로 이동
cd /home/jme09042/omok

# 1. 기존 프로세스 정리
echo "🛑 기존 프로세스 정리 중..."
pkill -f "python.*llm_server" 2>/dev/null
pkill -f "uvicorn.*main:app" 2>/dev/null
pkill -f "npm.*dev" 2>/dev/null
sleep 2

# 2. LLM 서버 백그라운드 실행
echo "🤖 LLM 서버 시작 중..."
cd backend
. .venv/bin/activate
nohup python llm_server.py > llm.log 2>&1 &
echo "   ✅ LLM 서버 시작됨 (PID: $!)"

# 3. 백엔드 서버 백그라운드 실행
echo "🔧 백엔드 서버 시작 중..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo "   ✅ 백엔드 서버 시작됨 (PID: $!)"

# 4. 프론트엔드 서버 백그라운드 실행
echo "🌐 프론트엔드 서버 시작 중..."
cd ../frontend
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &
echo "   ✅ 프론트엔드 서버 시작됨 (PID: $!)"

# 5. 완료 메시지
echo ""
echo "🎮 모든 서버가 백그라운드에서 실행 중입니다!"
echo "🌍 접속: http://$(curl -s ifconfig.me):5173"
echo "📚 API: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "📋 로그 확인:"
echo "   tail -f backend/llm.log"
echo "   tail -f backend/backend.log"
echo "   tail -f frontend/frontend.log"
