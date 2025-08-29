#!/bin/bash

# Ubuntu 환경에서 Omok 게임 서버 완전 재시작 스크립트

echo "🔄 Omok 게임 서버 완전 재시작 중..."
echo "======================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1단계: 모든 관련 프로세스 완전 종료
log_info "1단계: 기존 서버 프로세스 종료 중..."

# LLM 서버 프로세스 종료
log_info "   🤖 LLM 서버 프로세스 종료 중..."
pkill -f "python.*llm_server" 2>/dev/null
if [ $? -eq 0 ]; then
    log_success "   LLM 서버 프로세스 종료됨"
else
    log_warning "   LLM 서버 프로세스가 실행 중이지 않았습니다"
fi

# 백엔드 서버 프로세스 종료
log_info "   🔧 백엔드 서버 프로세스 종료 중..."
pkill -f "uvicorn.*main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    log_success "   백엔드 서버 프로세스 종료됨"
else
    log_warning "   백엔드 서버 프로세스가 실행 중이지 않았습니다"
fi

# 프론트엔드 서버 프로세스 종료
log_info "   🌐 프론트엔드 서버 프로세스 종료 중..."
pkill -f "npm.*dev" 2>/dev/null
if [ $? -eq 0 ]; then
    log_success "   프론트엔드 서버 프로세스 종료됨"
else
    log_warning "   프론트엔드 서버 프로세스가 실행 중이지 않았습니다"
fi

# Node.js 관련 프로세스 종료 (혹시 남아있을 수 있음)
log_info "   📱 Node.js 관련 프로세스 정리 중..."
pkill -f "node.*vite" 2>/dev/null
pkill -f "vite" 2>/dev/null

# 2단계: 포트 정리
log_info "2단계: 포트 정리 중..."

# 포트 8000, 8001, 5173 사용 중인 프로세스 강제 종료
for port in 8000 8001 5173; do
    PID=$(sudo lsof -t -i:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        log_warning "   포트 $port 사용 중인 프로세스(PID: $PID) 강제 종료"
        sudo kill -9 $PID 2>/dev/null
    else
        log_success "   포트 $port 정리됨"
    fi
done

# 3단계: 잠시 대기
log_info "3단계: 프로세스 정리 완료 대기 중..."
sleep 3

# 4단계: 프로세스 상태 확인
log_info "4단계: 프로세스 정리 상태 확인..."

# 남아있는 프로세스 확인
REMAINING_LLM=$(ps aux | grep "python.*llm_server" | grep -v grep | wc -l)
REMAINING_BACKEND=$(ps aux | grep "uvicorn.*main:app" | grep -v grep | wc -l)
REMAINING_FRONTEND=$(ps aux | grep "npm.*dev\|node.*vite" | grep -v grep | wc -l)

if [ $REMAINING_LLM -eq 0 ] && [ $REMAINING_BACKEND -eq 0 ] && [ $REMAINING_FRONTEND -eq 0 ]; then
    log_success "   모든 프로세스가 정리되었습니다"
else
    log_warning "   일부 프로세스가 여전히 실행 중입니다"
    ps aux | grep -E "(llm_server|uvicorn.*main:app|npm.*dev|node.*vite)" | grep -v grep
fi

# 5단계: 포트 상태 확인
log_info "5단계: 포트 상태 확인..."
for port in 8000 8001 5173; do
    if sudo lsof -i:$port >/dev/null 2>&1; then
        log_error "   포트 $port가 여전히 사용 중입니다"
    else
        log_success "   포트 $port가 사용 가능합니다"
    fi
done

# 6단계: 서버 재시작
log_info "6단계: 서버 재시작 중..."
echo ""

# 프로젝트 루트로 이동
cd /home/jme09042/omok

# azure_start.sh 실행
if [ -f "azure_start.sh" ]; then
    log_info "   azure_start.sh 실행 중..."
    bash azure_start.sh
else
    log_error "   azure_start.sh 파일을 찾을 수 없습니다"
    log_info "   수동으로 서버를 시작해야 합니다"
    
    # 수동 시작 가이드
    echo ""
    echo "📋 수동 시작 가이드:"
    echo "   1. 터미널 1: cd backend && . .venv/bin/activate && python llm_server.py"
    echo "   2. 터미널 2: cd backend && . .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000"
    echo "   3. 터미널 3: cd frontend && npm run dev -- --host 0.0.0.0"
fi

echo ""
log_success "재시작 프로세스가 완료되었습니다!"
