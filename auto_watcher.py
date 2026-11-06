#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-

"""
=============================================================================
[북 리딩 로그 실시간 폴더 감시자 (auto_watcher.py)]
- 역할: 현재 폴더 및 모든 연도/월 하위 폴더를 1초 주기로 실시간 감시합니다.
        새로운 독서 비평 HTML 파일이 추가되거나 기존 파일이 수정/삭제되면,
        즉시 build_dashboard.py를 호출하여 대시보드 데이터를 최신으로 자동 갱신합니다.
- 실행법: 터미널에서 python3 auto_watcher.py
          (또는 '대시보드_자동업데이트_실행.command' 더블클릭)
=============================================================================
"""

import os
import time
import subprocess
import sys
import unicodedata

# 1. 감시할 폴더 및 빌더 스크립트 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(CURRENT_DIR, "build_dashboard.py")

def get_html_files_snapshot(folder_path):
    """
    폴더 내의 모든 하위 디렉토리를 재귀 스캔하여
    독서 리뷰 HTML 파일의 {상대경로: 최종수정시각} 스냅샷 사전을 반환합니다.
    (단, index.html 및 시스템 가이드라인은 제외)
    """
    snapshot = {}
    try:
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            for f in files:
                if f.lower().endswith('.html'):
                    lower_name = f.lower()
                    if lower_name.startswith('index') or 'guideline' in lower_name:
                        continue
                    full_p = os.path.join(root, f)
                    rel_p = unicodedata.normalize('NFC', os.path.relpath(full_p, folder_path))
                    snapshot[rel_p] = os.path.getmtime(full_p)
    except Exception as e:
        print(f"⚠️ 폴더 스캔 중 일시적 오류 (무시 가능): {e}", flush=True)
    return snapshot

def run_build():
    """
    build_dashboard.py 스크립트를 실행하여 대시보드 데이터를 재생성하는 함수
    """
    try:
        result = subprocess.run(
            [sys.executable, BUILD_SCRIPT],
            cwd=CURRENT_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] ⚡ [자동 빌드 완료] 대시보드 데이터(dashboard_data.js)가 최신으로 갱신되었습니다!", flush=True)
        else:
            print(f"❌ 빌드 실패:\n{result.stderr}", flush=True)
    except Exception as e:
        print(f"❌ 빌드 실행 에러: {e}", flush=True)

def main():
    print("=" * 65, flush=True)
    print("🤖 [북 리딩 로그 실시간 자동 감시자 가동 시작]", flush=True)
    print(f"📁 감시 대상 루트 폴더: {CURRENT_DIR}", flush=True)
    print("ℹ️  연도별/월별 폴더에 새 독서 HTML을 넣기만 하면 즉시 대시보드에 반영됩니다.", flush=True)
    print("ℹ️  종료하려면 터미널 창에서 Ctrl + C 를 누르거나 창을 닫으세요.", flush=True)
    print("=" * 65, flush=True)

    # 최초 1회 즉시 빌드 수행하여 현재 상태 보장
    run_build()

    # 현재 파일 상태 스냅샷 저장
    last_snapshot = get_html_files_snapshot(CURRENT_DIR)
    print(f"👀 현재 감시 중인 도서 리뷰 수: {len(last_snapshot)}권", flush=True)
    print("-----------------------------------------------------------------", flush=True)

    # 1초 주기로 폴더 변경 사항 감시 루프
    try:
        while True:
            time.sleep(1.0)
            current_snapshot = get_html_files_snapshot(CURRENT_DIR)

            added_files = set(current_snapshot.keys()) - set(last_snapshot.keys())
            removed_files = set(last_snapshot.keys()) - set(current_snapshot.keys())

            modified_files = set()
            for path, mtime in current_snapshot.items():
                if path in last_snapshot and mtime > last_snapshot[path]:
                    modified_files.add(path)

            if added_files or removed_files or modified_files:
                current_time = time.strftime("%H:%M:%S")
                print(f"\n🔔 [{current_time}] 폴더 변경 감지됨!", flush=True)
                
                if added_files:
                    for f in added_files:
                        print(f"  ➕ 신규 도서 리뷰 감지: {f}", flush=True)
                if modified_files:
                    for f in modified_files:
                        print(f"  ✏️ 도서 리뷰 수정 감지: {f}", flush=True)
                if removed_files:
                    for f in removed_files:
                        print(f"  🗑️ 도서 리뷰 삭제 감지: {f}", flush=True)

                # 파일 변경이 감지되면 즉시 빌드 실행
                run_build()

                # 최신 스냅샷으로 갱신
                last_snapshot = current_snapshot
                print("-----------------------------------------------------------------", flush=True)

    except KeyboardInterrupt:
        print("\n👋 자동 감시자가 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()

