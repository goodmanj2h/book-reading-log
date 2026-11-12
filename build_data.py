#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
📖 [독서 기록 대시보드 데이터 빌더 (build_data.py)]
- 역할: 현재 디렉토리의 독서록 HTML 파일들을 스캔하여 최신 books_data.json을 생성합니다.
- GitHub Pages 배포 전 최신 데이터 동기화용으로 사용됩니다.
=============================================================================
"""

import sys
from pathlib import Path

# 현재 스크립트 위치를 파이썬 모듈 검색 경로에 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import server

def main():
    print("=" * 60)
    print(" 📦 독서 대시보드 정적 데이터 빌더 (build_data.py)")
    print("=" * 60)
    
    success = server.scan_directory()
    if success:
        print(f" ✅ 최신 독서록 데이터가 성공적으로 생성되었습니다: {server.BOOKS_DATA_FILE}")
        print(f"    총 {len(server.books_data)}권의 독서 기록이 동기화되었습니다.")
    else:
        print(" ❌ 데이터 빌드 중 오류가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
