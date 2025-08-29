#!/bin/bash

# OpenAI API 키 및 환경변수 설정 스크립트
# Azure Ubuntu VM에서 실행

echo "🔑 OpenAI API 키 및 환경변수 설정 중..."

# OpenAI API 키 입력 받기
echo "OpenAI API 키를 입력하세요 (sk-로 시작):"
read -s OPENAI_API_KEY

# 환경변수 설정
export OPENAI_API_KEY="$OPENAI_API_KEY"
export OMOK_LLM_MODEL="gpt-4o-mini"
export OMOK_LLM_DEBUG="1"
export OMOK_LLM_DEBUG_PROMPT="lite"
export OMOK_BOARD_SIZE="15"
export OMOK_LLM_N_CANDS="3"
export OMOK_CAND_MIN_DIST="2"
export OMOK_HISTORY_MAX="16"
export OMOK_LLM_MAX_TOKENS="700"
export OMOK_LLM_RETRY_MAX_TOKENS="1200"

# .bashrc에 환경변수 추가 (영구 설정)
echo "" >> ~/.bashrc
echo "# Omok 게임 환경변수" >> ~/.bashrc
echo "export OPENAI_API_KEY=\"$OPENAI_API_KEY\"" >> ~/.bashrc
echo "export OMOK_LLM_MODEL=\"gpt-4o-mini\"" >> ~/.bashrc
echo "export OMOK_LLM_DEBUG=\"1\"" >> ~/.bashrc
echo "export OMOK_LLM_DEBUG_PROMPT=\"lite\"" >> ~/.bashrc
echo "export OMOK_BOARD_SIZE=\"15\"" >> ~/.bashrc
echo "export OMOK_LLM_N_CANDS=\"3\"" >> ~/.bashrc
echo "export OMOK_CAND_MIN_DIST=\"2\"" >> ~/.bashrc
echo "export OMOK_HISTORY_MAX=\"16\"" >> ~/.bashrc
echo "export OMOK_LLM_MAX_TOKENS=\"700\"" >> ~/.bashrc
echo "export OMOK_LLM_RETRY_MAX_TOKENS=\"1200\"" >> ~/.bashrc

echo ""
echo "✅ 환경변수가 설정되었습니다!"
echo "🔑 OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo "🤖 모델: $OMOK_LLM_MODEL"
echo "🐛 디버그 모드: 활성화"
echo ""
echo "📝 영구 설정을 위해 다음 명령어를 실행하세요:"
echo "   source ~/.bashrc"
echo ""
echo "🎮 이제 게임을 시작할 수 있습니다:"
echo "   ./azure_start.sh"
