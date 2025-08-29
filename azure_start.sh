
#!/bin/bash

# Azure VM에서 Omok 게임 실행 스크립트

echo "🚀 Azure VM에서 Omok 게임 시작..."

# Azure VM IP 주소 가져오기
AZURE_IP=$(curl -s ifconfig.me)
echo "🌐 Azure VM IP 주소: $AZURE_IP"

# LLM 서버 먼저 시작 (백그라운드)
echo "🤖 LLM 서버 시작 중..."
cd /home/jme09042/omok/backend

# 가상환경 활성화 (절대 경로 사용)
if [ -d "/home/jme09042/omok/backend/.venv" ]; then
    source /home/jme09042/omok/backend/.venv/bin/activate
    echo "✅ 가상환경 활성화됨"
else
    echo "❌ 가상환경이 없습니다. 먼저 setup.sh를 실행하세요."
    exit 1
fi

# LLM 서버를 백그라운드에서 실행
echo "🤖 LLM 서버 시작..."
python llm_server.py &
LLM_PID=$!
echo "✅ LLM 서버 시작됨 (PID: $LLM_PID)"

# LLM 서버가 완전히 시작될 때까지 대기
echo "⏳ LLM 서버 초기화 대기 중..."
sleep 5

# LLM 서버 상태 확인
if ! kill -0 $LLM_PID 2>/dev/null; then
    echo "❌ LLM 서버가 시작되지 않았습니다. 로그를 확인하세요."
    exit 1
fi

echo "✅ LLM 서버가 정상적으로 실행 중입니다."

# 백엔드 시작
echo "🔧 백엔드 서버 시작 중..."
cd /home/jme09042/omok/backend

# 가상환경 활성화 (절대 경로 사용)
if [ -d "/home/jme09042/omok/backend/.venv" ]; then
    source /home/jme09042/omok/backend/.venv/bin/activate
    echo "✅ 가상환경 활성화됨"
else
    echo "❌ 가상환경이 없습니다. 먼저 setup.sh를 실행하세요."
    exit 1
fi

# 백엔드를 백그라운드에서 실행
echo "🔧 백엔드 서버 시작..."
python main.py &
BACKEND_PID=$!
echo "✅ 백엔드 서버 시작됨 (PID: $BACKEND_PID)"

# 잠시 대기
sleep 3

# 프론트엔드 시작
echo "🌐 프론트엔드 시작 중..."
cd /home/jme09042/omok/frontend

# 프론트엔드를 백그라운드에서 실행 (외부 접근 허용)
echo "🎮 프론트엔드 서버 시작..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
echo "✅ 프론트엔드 시작됨 (PID: $FRONTEND_PID)"

echo ""
echo "🎮 Omok 게임이 Azure VM에서 시작되었습니다!"
echo "🤖 LLM 서버: http://127.0.0.1:8001 (내부용)"
echo "🔧 프론트엔드: http://0.0.0.0:5173"
echo "🔧 백엔드: http://0.0.0.0:8000"
echo "🌐 외부 접근: http://$AZURE_IP:5173"
echo "📚 API 문서: http://$AZURE_IP:8000/docs"
echo ""
echo "프로그램을 종료하려면 Ctrl+C를 누르세요."

# 프로세스 종료를 위한 트랩 설정
trap "echo '🛑 서버 종료 중...'; kill $LLM_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# 프로세스들이 실행 중인 동안 대기
wait
