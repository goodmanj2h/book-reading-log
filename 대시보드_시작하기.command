#!/bin/bash

# ==============================================================================
# 📖 독서 기록 대시보드 원클릭 실행 스크립트
# ==============================================================================

# 스크립트가 위치한 폴더로 이동합니다.
cd "$(dirname "$0")"

echo "=========================================================="
echo " 📖 독서 기록 대시보드 서비스를 시작합니다..."
echo "=========================================================="
echo " [PC 브라우저 접속] : http://localhost:3000"
echo " [모바일 외부 접속] : https://overjoyed-unrelated-manifesto.ngrok-free.dev"
echo " (종료하시려면 이 터미널 창에서 Ctrl + C를 누르세요)"
echo "=========================================================="

# 백그라운드에서 파이썬 서버 실행
python3 server.py &
SERVER_PID=$!

# 서버 시작 대기 (1초)
sleep 1

# Mac 기본 웹 브라우저로 대시보드 자동 열기
open "http://localhost:3000"

# ngrok 고정 도메인으로 터널링 실행 (외부 및 스마트폰 LTE/5G 접속용)
if [ -f "./ngrok" ]; then
    ./ngrok http --domain=overjoyed-unrelated-manifesto.ngrok-free.dev 3000
else
    echo "[알림] ngrok 파일이 없어 로컬 서버만 유지합니다."
    wait $SERVER_PID
fi

# 사용자가 창을 닫거나 종료(Ctrl+C)하면 파이썬 서버도 함께 종료합니다.
kill $SERVER_PID 2>/dev/null
