#!/bin/bash

PROJECT_ROOT="/home/jme09042/omok"

echo "🛑 모든 서버 프로세스 종료 중..."

pkill -9 node 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true
pkill -9 -f "python3 run.py" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true

sleep 3

echo "✅ 프로세스 정리 완료"

cd $PROJECT_ROOT

echo "📂 현재 위치: $(pwd)"
echo "📁 폴더 내용:"
ls -la | grep -E '(backend|frontend)'

echo "🚀 백엔드 서버 시작 중..."

if [ -d "$PROJECT_ROOT/backend" ]; then
    cd $PROJECT_ROOT/backend
    
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "✅ 가상환경 활성화됨"
    fi
    
    if [ -f "run.py" ]; then
        python3 run.py &
        BACKEND_PID=$!
        echo "✅ 백엔드 시작됨 (PID: $BACKEND_PID)"
        sleep 3
    else
        echo "❌ run.py 파일을 찾을 수 없음"
    fi
else
    echo "❌ backend 폴더를 찾을 수 없음"
fi

echo "🌐 프론트엔드 서버 시작 중..."

if [ -d "$PROJECT_ROOT/frontend" ]; then
    cd $PROJECT_ROOT/frontend
    
    if [ -f "package.json" ]; then
        npm run dev -- --host 0.0.0.0 &
        FRONTEND_PID=$!
        echo "✅ 프론트엔드 시작됨 (PID: $FRONTEND_PID)"
        sleep 3
    else
        echo "❌ package.json 파일을 찾을 수 없음"
    fi
else
    echo "❌ frontend 폴더를 찾을 수 없음"
fi

echo ""
echo "🎮 Omok 게임이 재시작되었습니다!"
echo "📱 프론트엔드: http://4.217.179.111:5173"
echo "🔧 백엔드: http://4.217.179.111:8000"

echo ""
echo "📊 현재 실행 상태:"
ps aux | grep -E "(python3 run\.py|npm run dev)" | grep -v grep

echo ""
echo "🔍 포트 사용 현황:"
ss -tlnp | grep -E ':(8000|5173)'

cd $PROJECT_ROOT

