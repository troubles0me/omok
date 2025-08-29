#!/bin/bash

# Azure VM에서 Omok 게임 초기 설정 스크립트

echo "🔧 Azure VM에서 Omok 게임 초기 설정 시작..."

# 시스템 패키지 업데이트
echo "📦 시스템 패키지 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# Python 및 pip 설치
echo "🐍 Python 및 pip 설치 중..."
sudo apt install -y python3 python3-pip python3-venv

# Node.js 및 npm 설치 (최신 LTS 버전)
echo "📱 Node.js 및 npm 설치 중..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Git 설치
echo "📚 Git 설치 중..."
sudo apt install -y git

# 방화벽 설정
echo "🔥 방화벽 설정 중..."
sudo ufw allow 8000  # 백엔드 포트
sudo ufw allow 5173  # 프론트엔드 포트
sudo ufw allow 22    # SSH 포트

# 백엔드 설정
echo "🔧 백엔드 설정 중..."
cd backend

# Python 가상환경 생성
echo "🐍 Python 가상환경 생성 중..."
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate

# 필요한 패키지 설치
echo "📦 Python 패키지 설치 중..."
pip install -r requirements.txt

# 프론트엔드 설정
echo "🌐 프론트엔드 설정 중..."
cd ../frontend

# Node.js 의존성 설치
echo "📱 Node.js 의존성 설치 중..."
npm install

# 실행 권한 설정
echo "🔐 실행 권한 설정 중..."
chmod +x ../azure_start.sh
chmod +x backend/run.py

echo ""
echo "✅ 초기 설정이 완료되었습니다!"
echo ""
echo "🎮 게임을 시작하려면 다음 명령어를 실행하세요:"
echo "   ./azure_start.sh"
echo ""
echo "📖 자세한 설정 방법은 AZURE_SETUP.md를 참조하세요."
