# Azure Ubuntu VM에서 Omok 게임 실행 가이드

## 🚀 사전 요구사항

- Ubuntu 20.04 LTS 이상
- Python 3.8 이상
- Node.js 16 이상
- Git

## 📦 시스템 패키지 설치

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 및 pip 설치
sudo apt install -y python3 python3-pip python3-venv

# Node.js 및 npm 설치 (최신 LTS 버전)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Git 설치
sudo apt install -y git

# 방화벽 설정 (필요시)
sudo ufw allow 8000  # 백엔드 포트
sudo ufw allow 5173  # 프론트엔드 포트
sudo ufw allow 22    # SSH 포트
```

## 🔧 프로젝트 설정

### 1. 프로젝트 클론 또는 업로드
```bash
# Git에서 클론하는 경우
git clone <your-repo-url>
cd omok-final

# 또는 파일을 직접 업로드한 경우
cd omok-final
```

### 2. 백엔드 설정
```bash
cd backend

# Python 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate

# 필요한 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (필요시)
cp .env.example .env  # .env.example이 있는 경우
# 또는 직접 .env 파일 생성
```

### 3. 프론트엔드 설정
```bash
cd ../frontend

# Node.js 의존성 설치
npm install

# 프로덕션 빌드 (선택사항)
npm run build
```

## 🚀 서버 실행

### 백엔드 실행
```bash
cd backend
source .venv/bin/activate
python run.py
```

### 프론트엔드 실행 (개발 모드)
```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

### 프론트엔드 실행 (프로덕션 모드)
```bash
cd frontend
npm run build
npx serve -s dist -l 5173
```

## 🌐 방화벽 및 보안 설정

### UFW 방화벽 설정
```bash
# 기본 정책 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 필요한 포트 허용
sudo ufw allow ssh
sudo ufw allow 8000  # 백엔드
sudo ufw allow 5173  # 프론트엔드

# 방화벽 활성화
sudo ufw enable
```

### 시스템 서비스로 등록 (선택사항)
```bash
# 백엔드 서비스 파일 생성
sudo nano /etc/systemd/system/omok-backend.service
```

서비스 파일 내용:
```ini
[Unit]
Description=Omok Backend Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/omok-final/backend
Environment=PATH=/home/ubuntu/omok-final/backend/.venv/bin
ExecStart=/home/ubuntu/omok-final/backend/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable omok-backend
sudo systemctl start omok-backend
```

## 📊 모니터링 및 로그

### 서비스 상태 확인
```bash
# 백엔드 서비스 상태
sudo systemctl status omok-backend

# 로그 확인
sudo journalctl -u omok-backend -f
```

### 프로세스 모니터링
```bash
# 실행 중인 프로세스 확인
ps aux | grep python
ps aux | grep node

# 포트 사용 현황
sudo netstat -tlnp | grep -E ':(8000|5173)'
```

## 🔍 문제 해결

### 일반적인 문제들

1. **포트 충돌**
   ```bash
   # 포트 사용 현황 확인
   sudo lsof -i :8000
   sudo lsof -i :5173
   ```

2. **권한 문제**
   ```bash
   # 파일 권한 확인 및 수정
   chmod +x backend/run.py
   chmod 755 backend/
   chmod 755 frontend/
   ```

3. **메모리 부족**
   ```bash
   # 메모리 사용량 확인
   free -h
   # 스왑 메모리 생성 (필요시)
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## 📝 환경 변수 설정

### .env 파일 예시
```bash
# backend/.env
OMOK_LLM_URL=http://127.0.0.1:8001/omok/move
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://your-azure-ip:5173
```

## 🎯 최적화 팁

1. **Nginx 리버스 프록시 설정** (프로덕션 환경)
2. **PM2 사용** (Node.js 프로세스 관리)
3. **Supervisor 사용** (Python 프로세스 관리)
4. **SSL 인증서 설정** (HTTPS)

## 📞 지원

문제가 발생하면 다음을 확인하세요:
- 로그 파일
- 시스템 리소스 사용량
- 네트워크 연결 상태
- 방화벽 설정
