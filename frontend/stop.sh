#!/bin/bash

echo "🛑 모든 서버 프로세스 종료 중..."

# 모든 관련 프로세스 종료
pkill -9 node 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "python run.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

echo "✅ 모든 서버가 종료되었습니다."

# 포트 정리 확인
echo "📊 포트 상태:"
ss -tlnp | grep -E ':(8000|5173|5174|5175)' || echo "모든 포트가 정리되었습니다."

