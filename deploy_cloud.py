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
import unicodedata

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

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

def is_git_installed():
    """맥북에 Git이 설치되어 있는지 확인"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False

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

    if not is_git_installed():
        print("❌ Git이 설치되어 있지 않습니다. 터미널에서 Xcode Command Line Tools를 확인해주세요.")
        return

    # 1. 기존 Git 설정 여부 확인
    git_dir = os.path.join(CURRENT_DIR, ".git")
    if not os.path.exists(git_dir):
        print("⚙️ Git 저장소를 초기화합니다 (git init)...")
        subprocess.run(["git", "init"], cwd=CURRENT_DIR, check=True)
        # 기본 브랜치를 main으로 설정
        subprocess.run(["git", "branch", "-M", "main"], cwd=CURRENT_DIR, check=True)

    remote_url = get_current_git_remote()

    if not remote_url:
        print("\n💡 아직 GitHub 원격 저장소와 연결되지 않았습니다.")
        print("   스마트폰으로 접속하기 위해 GitHub 저장소(Repository) 정보가 필요합니다.\n")
        
        username = input("👉 1. 사용자님의 GitHub 아이디(Username)를 입력하세요: ").strip()
        if not username:
            print("❌ 아이디가 입력되지 않아 배포가 중단되었습니다.")
            return

        repo_name = input("👉 2. 저장소(Repository) 이름을 입력하세요 [기본값: book-reading-log]: ").strip()
        if not repo_name:
            repo_name = "book-reading-log"

        repo_url = f"https://github.com/{username}/{repo_name}.git"
        pages_url = f"https://{username}.github.io/{repo_name}/"

        print(f"\n🔗 연결할 저장소 주소: {repo_url}")
        print(f"📱 스마트폰 접속 주소: {pages_url}")
        print("-" * 68)
        print("⚠️ [안내] 만약 GitHub 웹사이트(https://github.com/new)에")
        print(f"    [{repo_name}] 이라는 이름의 저장소를 아직 만들지 않으셨다면,")
        print("    GitHub 사이트에서 [Public] 저장소로 먼저 생성해 주셔야 합니다.")
        print("-" * 68)
        
        confirm = input("👉 계속 진행하시겠습니까? (y/n): ").strip().lower()
        if confirm != 'y':
            print("배포가 취소되었습니다.")
            return

        # remote 추가
        try:
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=CURRENT_DIR, check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=CURRENT_DIR, check=True)
    else:
        # 기존 연결된 URL에서 username과 repo 추출
        print(f"🔗 현재 연결된 GitHub 저장소: {remote_url}")
        # https://github.com/username/repo.git 또는 git@github.com:username/repo.git
        import re
        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', remote_url)
        if match:
            username = match.group(1)
            repo_name = match.group(2)
            pages_url = f"https://{username}.github.io/{repo_name}/"
        else:
            pages_url = "GitHub Pages 설정 주소"

    # 2. 파일 추가 및 커밋
    print("\n📦 [2단계] 변경된 모든 독서 리포트와 대시보드 파일을 묶는 중...")
    subprocess.run(["git", "add", "."], cwd=CURRENT_DIR, check=True)

    commit_msg = f"독서 대시보드 동기화 업데이트 ({time.strftime('%Y-%m-%d %H:%M:%S')})"
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=CURRENT_DIR, capture_output=True, text=True)
    if "nothing to commit" in res.stdout:
        print("  ℹ️ 새로운 변경 사항이 없어 기존 상태를 그대로 유지합니다.")
    else:
        print(f"  ✅ 변경 사항 커밋 완료: {commit_msg}")

    # 3. 깃허브 푸시
    print("\n🚀 [3단계] GitHub 클라우드로 업로드 중 (git push origin main)...")
    push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=CURRENT_DIR, capture_output=True, text=True)

    if push_res.returncode == 0:
        print("\n" + "=" * 68)
        print("🎉 [축하합니다! GitHub 클라우드 배포가 성공적으로 완료되었습니다]")
        print("=" * 68)
        print("📱 내 스마트폰에서 24시간 언제든 접속할 수 있는 주소:")
        print(f"\n   👉 {pages_url}\n")
        print("ℹ️  [첫 배포 시 꿀팁]")
        print("1. GitHub 저장소 페이지(Settings -> Pages)에서")
        print("   'Build and deployment'의 Branch를 'main'으로 설정하고 Save를 눌러주세요.")
        print("2. 1~2분 정도 후 스마트폰 브라우저(Safari 또는 Chrome)에서 위 주소로 접속하세요.")
        print("3. 브라우저의 [공유 버튼(또는 메뉴)] -> [홈 화면에 추가]를 누르시면,")
        print("   스마트폰 바탕화면에 진짜 독서 앱처럼 아이콘이 생성됩니다!")
        print("=" * 68)
    else:
        print("\n⚠️ 깃허브 푸시 중 오류가 발생했습니다.")
        print(push_res.stderr)
        print("\n💡 원인 안내:")
        print("1. GitHub에 아직 해당 Repository가 생성되지 않았거나,")
        print("2. GitHub 로그인 인증(Personal Access Token 등)이 필요할 수 있습니다.")

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

