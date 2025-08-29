#!/bin/bash

# Azure VM에서 Omok 게임 실행 스크립트 (개선된 버전)

echo "🚀 Azure VM에서 Omok 게임 시작..."

# Azure VM IP 주소 가져오기
AZURE_IP=$(curl -s ifconfig.me)
echo "🌐 Azure VM IP 주소: $AZURE_IP"

# OpenAI API 키 확인
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY가 설정되지 않았습니다."
    echo "🔑 환경변수를 설정하려면 다음 명령어를 실행하세요:"
    echo "   chmod +x set_env.sh && ./set_env.sh"
    echo ""
    echo "또는 직접 설정:"
    echo "   export OPENAI_API_KEY='your_api_key_here'"
    exit 1
fi

# API 키 형식 확인
if [[ ! "$OPENAI_API_KEY" =~ ^sk-[a-zA-Z0-9]{48}$ ]]; then
    echo "❌ 잘못된 OpenAI API 키 형식입니다."
    echo "🔑 올바른 형식: sk-로 시작하는 51자리 문자열"
    echo "현재 키: ${OPENAI_API_KEY:0:20}..."
    exit 1
fi

echo "✅ OpenAI API 키가 올바르게 설정되었습니다."

# 백엔드 디렉토리로 이동
cd /home/jme09042/omok/backend

# 가상환경 확인 및 활성화
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 가상환경 활성화됨"
else
    echo "❌ 가상환경이 없습니다. 먼저 azure_setup.sh를 실행하세요."
    exit 1
fi

# 필요한 패키지 확인
if ! python -c "import openai" 2>/dev/null; then
    echo "📦 OpenAI 패키지 설치 중..."
    pip install openai python-dotenv
fi

# LLM 서버 시작
echo "🤖 LLM 서버 시작 중..."
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

# LLM 서버 연결 테스트
echo "🔍 LLM 서버 연결 테스트 중..."
if curl -s http://127.0.0.1:8001/__ping__ > /dev/null; then
    echo "✅ LLM 서버가 정상적으로 응답합니다."
else
    echo "❌ LLM 서버 연결 실패. 로그를 확인하세요."
    exit 1
fi

# 백엔드 시작
echo "🔧 백엔드 서버 시작 중..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 백엔드 서버 시작됨 (PID: $BACKEND_PID)"

# 잠시 대기
sleep 3

# 백엔드 서버 연결 테스트
echo "🔍 백엔드 서버 연결 테스트 중..."
if curl -s http://127.0.0.1:8000/docs > /dev/null; then
    echo "✅ 백엔드 서버가 정상적으로 응답합니다."
else
    echo "❌ 백엔드 서버 연결 실패. 로그를 확인하세요."
    exit 1
fi

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
echo "🔧 백엔드: http://0.0.0.0:8000"
echo "🌐 프론트엔드: http://0.0.0.0:5173"
echo "🌐 외부 접근: http://$AZURE_IP:5173"
echo "📚 API 문서: http://$AZURE_IP:8000/docs"
echo ""
echo "🔍 AI 기능 테스트:"
echo "   curl -X POST http://127.0.0.1:8000/api/game/test/ai-move \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"difficulty\":\"초급\"}'"
echo ""
echo "프로그램을 종료하려면 Ctrl+C를 누르세요."

# 프로세스 종료를 위한 트랩 설정
trap "echo '🛑 서버 종료 중...'; kill $LLM_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# 프로세스들이 실행 중인 동안 대기
wait
