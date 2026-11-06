#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-

"""
=============================================================================
[북 리딩 로그 24시간 모바일 클라우드 배포 도구 (deploy_cloud.py)]
- 역할: 내 맥북 컴퓨터가 꺼져 있어도 스마트폰으로 24시간 언제든 접속할 수 있도록
        GitHub Pages 무료 클라우드 호스팅에 대시보드를 배포하고 스마트폰 접속 주소를 발급합니다.
- 실행법: 터미널에서 python3 deploy_cloud.py
          (또는 '클라우드_배포하기.command' 더블클릭)
=============================================================================
"""

import os
import sys
import subprocess
import time
import webbrowser
import re

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_USERNAME = "goodmanj2h"
DEFAULT_REPO_NAME = "book-reading-log"

def print_banner():
    print("=" * 68)
    print("📱 [Book Reading Log 24시간 모바일 클라우드 배포 센터]")
    print("   '내 컴퓨터가 꺼져 있어도 스마트폰에서 언제든 접속 가능!'")
    print("=" * 68)

def run_pre_build():
    """배포 직전 build_dashboard.py를 실행하여 최신 데이터가 반영되었는지 확인"""
    print("\n📦 [1단계] 최신 독서 리포트 데이터 동기화 확인 중...")
    build_script = os.path.join(CURRENT_DIR, "build_dashboard.py")
    res = subprocess.run([sys.executable, build_script], cwd=CURRENT_DIR, capture_output=True, text=True)
    if res.returncode == 0:
        print("  ✅ 최신 독서 데이터(dashboard_data.js) 동기화 완료!")
    else:
        print(f"  ⚠️ 빌드 경고:\n{res.stderr}")

def get_current_git_remote():
    """현재 연결된 Git 원격 저장소 URL 확인"""
    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=CURRENT_DIR, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None

def deploy_github_pages():
    """
    GitHub 저장소로 코드를 푸시하여 24시간 무료 GitHub Pages로 배포하는 메인 루틴
    """
    print("\n" + "=" * 68)
    print("🐙 [GitHub Pages 24시간 무료 모바일 호스팅 배포]")
    print("=" * 68)

    # 1. 기존 Git 설정 여부 확인
    git_dir = os.path.join(CURRENT_DIR, ".git")
    if not os.path.exists(git_dir):
        print("⚙️ Git 저장소를 초기화합니다 (git init)...")
        subprocess.run(["git", "init"], cwd=CURRENT_DIR, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=CURRENT_DIR, check=True)

    remote_url = get_current_git_remote()
    username = DEFAULT_USERNAME
    repo_name = DEFAULT_REPO_NAME

    if remote_url:
        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', remote_url)
        if match:
            username = match.group(1)
            repo_name = match.group(2)
        else:
            # 올바르지 않은 원격 URL이면 기본값으로 재설정
            correct_url = f"https://github.com/{DEFAULT_USERNAME}/{DEFAULT_REPO_NAME}.git"
            subprocess.run(["git", "remote", "set-url", "origin", correct_url], cwd=CURRENT_DIR, check=True)
            username = DEFAULT_USERNAME
            repo_name = DEFAULT_REPO_NAME
    else:
        correct_url = f"https://github.com/{DEFAULT_USERNAME}/{DEFAULT_REPO_NAME}.git"
        subprocess.run(["git", "remote", "add", "origin", correct_url], cwd=CURRENT_DIR, check=True)

    pages_url = f"https://{username}.github.io/{repo_name}/"
    repo_web_url = f"https://github.com/{username}/{repo_name}"

    print(f"👤 GitHub 계정 : {username}")
    print(f"📁 저장소 이름 : {repo_name}")
    print(f"🔗 원격지 주소 : https://github.com/{username}/{repo_name}.git")
    print(f"📱 스마트폰 주소: {pages_url}")
    print("-" * 68)

    # 2. 파일 추가 및 커밋
    print("\n📦 [2단계] 변경된 모든 파일 커밋 중...")
    subprocess.run(["git", "add", "."], cwd=CURRENT_DIR, check=True)

    commit_msg = f"독서 대시보드 동기화 업데이트 ({time.strftime('%Y-%m-%d %H:%M:%S')})"
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=CURRENT_DIR, capture_output=True, text=True)
    if "nothing to commit" in res.stdout:
        print("  ℹ️ 최신 변경 사항이 이미 모두 커밋되어 있습니다.")
    else:
        print(f"  ✅ 커밋 완료: {commit_msg}")

    # 3. 깃허브 푸시 시도 루프
    print(f"\n🚀 [3단계] GitHub 클라우드로 업로드 중 (git push origin main)...")
    push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=CURRENT_DIR, capture_output=True, text=True)

    # 만약 저장소가 아직 없어서 실패한 경우 (not found)
    if push_res.returncode != 0 and ("not found" in push_res.stderr.lower() or "repository not found" in push_res.stderr.lower()):
        print("\n" + "!" * 68)
        print("💡 [원인 파악] GitHub 웹사이트에 아직 '방(저장소)'이 만들어지지 않았습니다!")
        print(f"   현재 깃허브 서버에 [{repo_name}] 이라는 이름의 저장소가 없어서 업로드가 대기 중입니다.")
        print("!" * 68)
        print("\n👉 해결 방법 (10초면 끝납니다):")
        print("1. 잠시 후 웹 브라우저로 [GitHub 새 저장소 만들기] 페이지가 자동으로 열립니다.")
        print(f"2. Repository name 칸에: {repo_name}  을 입력하세요.")
        print("3. [Public] 선택 상태 그대로 두고, 아래 초록색 [Create repository] 버튼을 누르세요.")
        print("   (※ README 파일 체크박스는 건드리지 마세요!)")
        print("-" * 68)
        
        input("👉 브라우저를 열 준비가 되셨으면 [엔터(Enter)]를 누르세요...")
        webbrowser.open(f"https://github.com/new?name={repo_name}")
        
        print("\n🌐 브라우저가 열렸습니다! 저장소를 생성하셨나요?")
        input("👉 생성 완료하셨으면 [엔터(Enter)]를 눌러 업로드를 다시 진행합니다...")
        
        print("\n🚀 다시 업로드를 시도합니다...")
        push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=CURRENT_DIR, capture_output=True, text=True)

    if push_res.returncode == 0:
        print("\n" + "=" * 68)
        print("🎉 [축하합니다! GitHub 클라우드 배포가 성공적으로 완료되었습니다]")
        print("=" * 68)
        print("📱 내 스마트폰에서 24시간 언제든 접속할 수 있는 주소:")
        print(f"\n   👉 {pages_url}\n")
        print("ℹ️  [첫 배포 시 딱 1번만 해주실 작업 (GitHub Pages 켜기)]")
        print(f"1. 브라우저에서 아래 설정 페이지로 이동하세요:")
        print(f"   {repo_web_url}/settings/pages")
        print("2. [Build and deployment] 아래의 [Source]가 'GitHub Actions' 또는")
        print("   'Deploy from a branch' (Branch: main, /root)로 되어 있는지 확인하고 저장하세요.")
        print("3. 1~2분 후 스마트폰 Safari/Chrome에서 위 주소로 접속하시면 끝입니다!")
        print("4. 브라우저 [공유] -> [홈 화면에 추가]를 누르면 진짜 앱으로 설치됩니다!")
        print("=" * 68)
        
        # 설정 페이지 자동 열기 옵션
        open_settings = input("\n👉 지금 바로 GitHub Pages 설정 페이지를 여시겠습니까? (y/n) [기본값: y]: ").strip().lower()
        if open_settings != 'n':
            webbrowser.open(f"{repo_web_url}/settings/pages")
    else:
        print("\n⚠️ 깃허브 푸시 실패 메시지:")
        print(push_res.stderr)
        print("\n💡 추가 도움이 필요하시면 안티그래비티 대화창에 위 에러 메시지를 알려주세요.")

def main():
    print_banner()
    run_pre_build()

    print("\n어떤 작업을 진행하시겠습니까?")
    print("1. 🐙 GitHub Pages 클라우드에 24시간 배포하기 (추천)")
    print("2. 🌐 내 맥북 브라우저에서 로컬 대시보드 바로 열기")
    print("3. ❌ 종료")
    
    choice = input("\n👉 번호를 선택하세요 (1/2/3) [기본값: 1]: ").strip()
    if not choice or choice == "1":
        deploy_github_pages()
    elif choice == "2":
        index_file = os.path.join(CURRENT_DIR, "index.html")
        webbrowser.open(f"file://{index_file}")
        print("✅ 브라우저에서 로컬 대시보드가 열렸습니다.")
    else:
        print("종료합니다.")

if __name__ == "__main__":
    main()
