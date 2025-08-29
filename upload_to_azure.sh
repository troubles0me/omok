#!/bin/bash

# Azure VM에 Omok 프로젝트 업로드 스크립트

echo "🚀 Azure VM에 Omok 프로젝트 업로드 준비 중..."

# Azure VM IP 주소 입력 받기
read -p "Azure VM의 공용 IP 주소를 입력하세요: " AZURE_IP
read -p "Azure VM 사용자명을 입력하세요 (기본값: ubuntu): " AZURE_USER
AZURE_USER=${AZURE_USER:-ubuntu}

echo "📤 $AZURE_USER@$AZURE_IP 에 업로드합니다..."

# 불필요한 폴더들을 제외하고 압축
echo "📦 프로젝트 압축 중..."
tar -czf omok-final.tar.gz \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='dist' \
  --exclude='*.log' \
  --exclude='.git' \
  .

# Azure VM에 업로드
echo "📤 Azure VM에 업로드 중..."
scp omok-final.tar.gz $AZURE_USER@$AZURE_IP:/home/$AZURE_USER/

if [ $? -eq 0 ]; then
    echo "✅ 업로드 완료!"
    echo ""
    echo "🎯 다음 단계:"
    echo "1. Azure VM에 SSH 접속:"
    echo "   ssh $AZURE_USER@$AZURE_IP"
    echo ""
    echo "2. VM에서 압축 해제:"
    echo "   cd /home/$AZURE_USER"
    echo "   tar -xzf omok-final.tar.gz"
    echo "   cd omok-final"
    echo ""
    echo "3. 초기 설정 실행:"
    echo "   chmod +x azure_setup.sh"
    echo "   ./azure_setup.sh"
    echo ""
    echo "4. 게임 실행:"
    echo "   ./azure_start.sh"
else
    echo "❌ 업로드 실패!"
    echo "Azure VM의 IP 주소와 SSH 키를 확인해주세요."
fi

# 임시 압축 파일 삭제
rm omok-final.tar.gz
echo "🧹 임시 파일 정리 완료"
