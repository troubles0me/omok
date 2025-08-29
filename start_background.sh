#!/bin/bash

# 모든 Omok 서버를 백그라운드로 실행하는 스크립트

echo "🚀 Omok 게임 서버 백그라운드 실행 시작..."
echo "=========================================="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수: 로그 출력
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 프로젝트 루트로 이동
cd /home/jme09042/omok

# 1단계: LLM 서버 백그라운드 실행
log_info "1단계: LLM 서버 시작 중..."
cd backend
. .venv/bin/activate

# 기존 LLM 서버 프로세스 종료
pkill -f "python.*llm_server" 2>/dev/null
sleep 1

# LLM 서버 백그라운드 실행
nohup python llm_server.py > llm.log 2>&1 &
LLM_PID=$!
echo "   🤖 LLM 서버 시작됨 (PID: $LLM_PID, 로그: llm.log)"

# LLM 서버 초기화 대기
log_info "   ⏳ LLM 서버 초기화 대기 중..."
sleep 5

# LLM 서버 상태 확인
if kill -0 $LLM_PID 2>/dev/null; then
    log_success "   ✅ LLM 서버가 정상적으로 실행 중입니다"
else
    log_warning "   ⚠️ LLM 서버 시작에 문제가 있을 수 있습니다"
fi

# 2단계: 백엔드 서버 백그라운드 실행
log_info "2단계: 백엔드 서버 시작 중..."

# 기존 백엔드 프로세스 종료
pkill -f "uvicorn.*main:app" 2>/dev/null
sleep 1

# 백엔드 서버 백그라운드 실행
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   🔧 백엔드 서버 시작됨 (PID: $BACKEND_PID, 로그: backend.log)"

# 백엔드 서버 초기화 대기
log_info "   ⏳ 백엔드 서버 초기화 대기 중..."
sleep 3

# 백엔드 서버 상태 확인
if kill -0 $BACKEND_PID 2>/dev/null; then
    log_success "   ✅ 백엔드 서버가 정상적으로 실행 중입니다"
else
    log_warning "   ⚠️ 백엔드 서버 시작에 문제가 있을 수 있습니다"
fi

# 3단계: 프론트엔드 서버 백그라운드 실행
log_info "3단계: 프론트엔드 서버 시작 중..."
cd ../frontend

# 기존 프론트엔드 프로세스 종료
pkill -f "npm.*dev" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
sleep 1

# 프론트엔드 서버 백그라운드 실행
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   🌐 프론트엔드 서버 시작됨 (PID: $FRONTEND_PID, 로그: frontend.log)"

# 프론트엔드 서버 초기화 대기
log_info "   ⏳ 프론트엔드 서버 초기화 대기 중..."
sleep 5

# 프론트엔드 서버 상태 확인
if kill -0 $FRONTEND_PID 2>/dev/null; then
    log_success "   ✅ 프론트엔드 서버가 정상적으로 실행 중입니다"
else
    log_warning "   ⚠️ 프론트엔드 서버 시작에 문제가 있을 수 있습니다"
fi

# 4단계: 최종 상태 확인
log_info "4단계: 최종 상태 확인 중..."

# Azure VM IP 주소 가져오기
AZURE_IP=$(curl -s ifconfig.me 2>/dev/null || echo "확인 불가")

# 프로세스 상태 요약
echo ""
echo "🎮 Omok 게임 서버 백그라운드 실행 완료!"
echo "========================================"
echo "🤖 LLM 서버:"
echo "   - PID: $LLM_PID"
echo "   - 포트: 8001 (내부용)"
echo "   - 로그: backend/llm.log"
echo "   - 상태: $(kill -0 $LLM_PID 2>/dev/null && echo "✅ 실행 중" || echo "❌ 중단됨")"

echo ""
echo "🔧 백엔드 서버:"
echo "   - PID: $BACKEND_PID"
echo "   - 포트: 8000"
echo "   - 로그: backend/backend.log"
echo "   - 상태: $(kill -0 $BACKEND_PID 2>/dev/null && echo "✅ 실행 중" || echo "❌ 중단됨")"

echo ""
echo "🌐 프론트엔드 서버:"
echo "   - PID: $FRONTEND_PID"
echo "   - 포트: 5173"
echo "   - 로그: frontend/frontend.log"
echo "   - 상태: $(kill -0 $FRONTEND_PID 2>/dev/null && echo "✅ 실행 중" || echo "❌ 중단됨")"

echo ""
echo "🌍 접속 정보:"
echo "   - 프론트엔드: http://$AZURE_IP:5173"
echo "   - 백엔드 API: http://$AZURE_IP:8000"
echo "   - API 문서: http://$AZURE_IP:8000/docs"

echo ""
echo "📋 유용한 명령어:"
echo "   - 로그 확인: tail -f backend/llm.log"
echo "   - 로그 확인: tail -f backend/backend.log"
echo "   - 로그 확인: tail -f frontend/frontend.log"
echo "   - 프로세스 확인: ps aux | grep -E '(python.*llm_server|uvicorn.*main:app|npm.*dev)'"
echo "   - 포트 확인: sudo netstat -tlnp | grep -E ':(8000|8001|5173)'"

echo ""
log_success "모든 서버가 백그라운드에서 실행 중입니다!"
echo "   이제 터미널을 닫아도 서버가 계속 실행됩니다."
