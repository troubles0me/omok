#!/bin/bash

echo "📊 Omok 게임 서버 상태"
echo "=========================="

echo ""
echo "🔍 실행 중인 프로세스:"
ps aux | grep -E "(python run\.py|npm run dev)" | grep -v grep || echo "실행 중인 서버가 없습니다."

echo ""
echo "🔍 포트 사용 현황:"
ss -tlnp | grep -E ':(8000|5173)' || echo "서버 포트가 사용되지 않습니다."

echo ""
echo "🌐 접속 정보:"
echo "📱 프론트엔드: http://4.217.179.111:5173"
echo "🔧 백엔드: http://4.217.179.111:8000"
echo "📊 API 문서: http://4.217.179.111:8000/docs"

