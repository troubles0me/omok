#!/bin/bash

echo "🛑 모든 서버 프로세스 종료 중..."

# 1. 모든 Node.js 프로세스 강제 종료
pkill -9 node 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true

# 2. Python 서버 프로세스 종료
pkill -9 -f "python3 run.py" 2>/dev/null || true
pkill -9 -f "python run.py" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true

# 3. 잠시 대기
sleep 3

echo "✅ 프로세스 정리 완료"

# 4. 현재 위치 확인
echo "📂 현재 위치: $(pwd)"
echo "📁 폴더 내용: $(ls -la | grep -E '(backend|frontend)')"

# 5. 포트 정리 확인
echo "📊 포트 정리 상태:"
ss -tlnp | grep -E ':(8000|5173|5174|5175)' || echo "모든 포트가 정리되었습니다."

echo ""
echo "🚀 백엔드 서버 시작 중..."

# 6. 백엔드 시작 (절대 경로 사용)
if [ -d "backend" ]; then
    cd backend
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "✅ 가상환경 활성화됨"
    else
        echo "❌ 가상환경을 찾을 수 없음"
    fi
    
    if [ -f "run.py" ]; then
        python3 run.py &
        BACKEND_PID=$!
        echo "✅ 백엔드 시작됨 (PID: $BACKEND_PID)"
    else
        echo "❌ run.py 파일을 찾을 수 없음"
    fi
    cd ..
else
    echo "❌ backend 폴더를 찾을 수 없음"
fi

# 7. 백엔드 시작 대기
sleep 5

echo "🌐 프론트엔드 서버 시작 중..."

# 8. 프론트엔드 시작
if [ -d "frontend" ]; then
    cd frontend
    if [ -f "package.json" ]; then
        npm run dev -- --host 0.0.0.0 &
        FRONTEND_PID=$!
        echo "✅ 프론트엔드 시작됨 (PID: $FRONTEND_PID)"
    else
        echo "❌ package.json 파일을 찾을 수 없음"
    fi
    cd ..
else
    echo "❌ frontend 폴더를 찾을 수 없음"
fi

# 9. 프론트엔드 시작 대기
sleep 5

echo ""
echo "🎮 Omok 게임이 재시작되었습니다!"
echo "📱 프론트엔드: http://4.217.179.111:5173"
echo "🔧 백엔드: http://4.217.179.111:8000"
echo "📊 API 문서: http://4.217.179.111:8000/docs"

echo ""
echo "📊 현재 실행 상태:"
ps aux | grep -E "(python3 run\.py|npm run dev)" | grep -v grep

echo ""
echo "🔍 포트 사용 현황:"
ss -tlnp | grep -E ':(8000|5173)'

