#!/bin/bash

# ==============================================================================
# 🐙 독서 기록 대시보드 24시간 스마트폰 클라우드 자동 배포 스크립트
# - 맥북이 꺼져 있어도 스마트폰에서 언제든 접속 가능!
# - 더블클릭 한 번으로 GitHub Pages 클라우드에 최신 독서록을 동기화합니다.
# ==============================================================================

# 스크립트가 위치한 폴더로 이동
cd "$(dirname "$0")"

echo "=========================================================="
echo " 📱 [독서 대시보드 24시간 모바일 클라우드 배포 센터]"
echo "    '컴퓨터가 꺼져 있어도 스마트폰에서 언제든 접속 가능!'"
echo "=========================================================="

# 1. 최신 독서록 데이터 빌드
echo ""
echo "📦 [1단계] 최신 독서 기록 스캔 및 데이터 동기화 중..."
python3 build_data.py

if [ $? -ne 0 ]; then
    echo "❌ 데이터 빌드 실패. 배포를 중단합니다."
    exit 1
fi

# 2. Git 원격지 주소 확인 및 설정
REPO_URL="https://github.com/goodmanj2h/book-reading-log.git"
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null)

if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
    echo ""
    echo "⚙️ [Git 설정] GitHub 원격 저장소를 연결합니다..."
    git remote remove origin 2>/dev/null
    git remote add origin "$REPO_URL"
fi

# 3. 변경 사항 커밋
echo ""
echo "📦 [2단계] 변경된 독서록 파일 커밋 준비 중..."
git add .

COMMIT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
git commit -m "독서 대시보드 및 독서록 동기화 업데이트 ($COMMIT_TIME)" >/dev/null 2>&1

# 4. GitHub로 푸시
echo ""
echo "🚀 [3단계] GitHub 클라우드로 업로드 중 (git push origin main)..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================================="
    echo " 🎉 [축하합니다! 클라우드 배포가 성공적으로 완료되었습니다!]"
    echo "=========================================================="
    echo " 📱 내 스마트폰에서 24시간 언제든 접속할 수 있는 주소:"
    echo ""
    echo "    👉 https://goodmanj2h.github.io/book-reading-log/"
    echo ""
    echo " 💡 스마트폰 사파리/크롬에서 위 주소 접속 후"
    echo "    [공유] -> [홈 화면에 추가]를 누르시면 진짜 앱으로 설치됩니다!"
    echo "=========================================================="
else
    echo ""
    echo "⚠️ 업로드 중 오류가 발생했습니다. 네트워크 연결을 확인해 주세요."
fi

echo ""
read -p "창을 닫으시려면 [Enter] 키를 누르세요..."
