# Azure Ubuntu VM 문제 해결 가이드

## 🔑 OpenAI API 키 오류 해결

### 문제: "Incorrect API key provided: sk-your_***************here"

**원인**: OpenAI API 키가 설정되지 않았거나 잘못된 형식입니다.

**해결 방법**:

1. **환경변수 설정 스크립트 실행**:
   ```bash
   chmod +x set_env.sh
   ./set_env.sh
   ```

2. **직접 환경변수 설정**:
   ```bash
   export OPENAI_API_KEY='sk-your_actual_api_key_here'
   ```

3. **영구 설정** (재부팅 후에도 유지):
   ```bash
   echo "export OPENAI_API_KEY='sk-your_actual_api_key_here'" >> ~/.bashrc
   source ~/.bashrc
   ```

### API 키 형식 확인
- 올바른 형식: `sk-`로 시작하는 51자리 문자열
- 예시: `sk-1234567890abcdef1234567890abcdef1234567890abcdef`

## 🚀 서버 시작 문제 해결

### LLM 서버 시작 실패

1. **가상환경 확인**:
   ```bash
   cd /home/jme09042/omok/backend
   ls -la .venv/
   ```

2. **가상환경 재생성**:
   ```bash
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **필요한 패키지 설치**:
   ```bash
   pip install openai python-dotenv fastapi uvicorn
   ```

### 백엔드 서버 시작 실패

1. **포트 충돌 확인**:
   ```bash
   sudo lsof -i :8000
   sudo lsof -i :8001
   ```

2. **프로세스 종료**:
   ```bash
   pkill -f "python.*llm_server.py"
   pkill -f "uvicorn.*main:app"
   ```

3. **로그 확인**:
   ```bash
   cat backend.log
   ```

## 🔍 연결 테스트

### LLM 서버 테스트
```bash
curl http://127.0.0.1:8001/__ping__
```

### 백엔드 서버 테스트
```bash
curl http://127.0.0.1:8000/docs
```

### AI 기능 테스트
```bash
curl -X POST http://127.0.0.1:8000/api/game/test/ai-move \
  -H "Content-Type: application/json" \
  -d '{"difficulty":"초급"}'
```

## 📊 시스템 상태 확인

### 프로세스 확인
```bash
ps aux | grep python
ps aux | grep node
```

### 포트 사용 현황
```bash
sudo netstat -tlnp | grep -E ':(8000|8001|5173)'
```

### 메모리 사용량
```bash
free -h
df -h
```

## 🛠️ 일반적인 문제들

### 1. 권한 문제
```bash
chmod +x *.sh
chmod 755 backend/ frontend/
```

### 2. 방화벽 설정
```bash
sudo ufw allow 8000  # 백엔드
sudo ufw allow 8001  # LLM 서버
sudo ufw allow 5173  # 프론트엔드
sudo ufw status
```

### 3. Python 버전 문제
```bash
python3 --version
python --version
# Python 3.8 이상 필요
```

### 4. Node.js 버전 문제
```bash
node --version
npm --version
# Node.js 16 이상 필요
```

## 🔄 완전 재설정

문제가 지속되면 완전 재설정:

```bash
# 1. 모든 프로세스 종료
pkill -f "python.*llm_server.py"
pkill -f "uvicorn.*main:app"
pkill -f "npm.*dev"

# 2. 가상환경 재생성
cd /home/jme09042/omok/backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 환경변수 설정
./set_env.sh

# 4. 서버 재시작
./azure_start_improved.sh
```

## 📞 추가 지원

문제가 해결되지 않으면:

1. **로그 파일 확인**: `backend.log`, `llm_server.py` 출력
2. **시스템 리소스 확인**: CPU, 메모리, 디스크 공간
3. **네트워크 연결 확인**: 방화벽, 포트 상태
4. **OpenAI 계정 상태 확인**: API 키 유효성, 사용량 한도
