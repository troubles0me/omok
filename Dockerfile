# Python 베이스 이미지
FROM python:3.10-slim

# 컨테이너 작업 디렉토리
WORKDIR /app

# Python 의존성 설치
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 복사
COPY backend ./backend

# 프론트엔드 복사 및 빌드
COPY frontend ./frontend
RUN apt-get update && apt-get install -y nodejs npm \
    && cd frontend && npm install && npm run build

# dist를 backend 안으로 복사하지 않고 그대로 사용
# FastAPI가 frontend/dist를 서빙하도록 수정 필요
# (main.py 에서 directory 경로를 ../frontend/dist 로 지정해야 함)
# 예: frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")

# Python import 경로 보장
ENV PYTHONPATH=/app

# 포트 노출 (Azure는 기본적으로 8080을 사용함)
EXPOSE 8080

# FastAPI 실행 (PORT 환경변수 지원)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
