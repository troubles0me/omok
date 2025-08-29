# backend/config.py
import os

# 보드 크기 (기본 15x15)
OMOK_BOARD_SIZE = int(os.getenv("OMOK_BOARD_SIZE", "15"))

# LLM API 서버 설정 (초급에서 사용)
OMOK_LLM_URL = os.getenv("OMOK_LLM_URL", "http://127.0.0.1:8001/omok/move")
OMOK_LLM_KEY = os.getenv("OMOK_LLM_KEY", "")  # 프록시에 토큰이 필요하면 사용

# RL 모델 경로 (고급에서 사용)
OMOK_RL_PATH = os.getenv("OMOK_RL_PATH", "model.pt")
