#!/bin/bash

# 서버 상태 확인 스크립트

echo "🔍 Omok 게임 서버 상태 확인 중..."
echo "=================================="

# LLM 서버 상태 확인
echo "🤖 LLM 서버 (포트 8001):"
if curl -s http://127.0.0.1:8001/__ping__ > /dev/null 2>&1; then
    echo "   ✅ 정상 실행 중"
    LLM_STATUS=$(curl -s http://127.0.0.1:8001/__ping__ | python3 -m json.tool 2>/dev/null | grep -E '"model"|"board_size"' || echo "   📊 상태 정보 확인 불가")
    echo "   $LLM_STATUS"
else
    echo "   ❌ 실행되지 않음"
fi

echo ""

# 백엔드 서버 상태 확인
echo "🔧 백엔드 서버 (포트 8000):"
if curl -s http://127.0.0.1:8000/docs > /dev/null 2>&1; then
    echo "   ✅ 정상 실행 중"
else
    echo "   ❌ 실행되지 않음"
fi

echo ""

# 프론트엔드 서버 상태 확인
echo "🌐 프론트엔드 서버 (포트 5173):"
if curl -s http://127.0.0.1:5173 > /dev/null 2>&1; then
    echo "   ✅ 정상 실행 중"
else
    echo "   ❌ 실행되지 않음"
fi

echo ""

# 프로세스 상태 확인
echo "📊 프로세스 상태:"
echo "   LLM 서버:"
ps aux | grep "python.*llm_server" | grep -v grep | awk '{print "     PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "CMD:", $11}' || echo "     실행 중이 아님"

echo "   백엔드 서버:"
ps aux | grep "python.*main" | grep -v grep | awk '{print "     PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "CMD:", $11}' || echo "     실행 중이 아님"

echo "   프론트엔드 서버:"
ps aux | grep "npm.*dev" | grep -v grep | awk '{print "     PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "CMD:", $11}' || echo "     실행 중이 아님"

echo ""

# 포트 사용 현황
echo "🔌 포트 사용 현황:"
sudo netstat -tlnp | grep -E ':(8000|8001|5173)' | awk '{print "   포트", $4, "-> PID", $7}' 2>/dev/null || echo "   포트 정보 확인 불가"

echo ""
echo "✅ 상태 확인 완료!"
