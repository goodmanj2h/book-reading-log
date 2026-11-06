#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-

"""
=============================================================================
[북 리딩 로그 대시보드 데이터 빌더 (build_dashboard.py)]
- 역할: 현재 폴더 및 하위 연도/월 폴더를 탐색하여 모든 독서 리뷰 HTML 파일을 수집하고,
        책 제목, 저자, 독서일, 표지 이미지, 키워드/장르 배지, 핵심 인용구, 한줄평을 추출하여
        대시보드 전용 데이터 파일(dashboard_data.js)을 생성합니다.
- 실행법: 터미널에서 python3 build_dashboard.py
=============================================================================
"""

import os
import re
import json
import datetime
import unicodedata
from html import unescape

# 1. 기준 디렉토리 설정 (스크립트가 위치한 현재 폴더)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DATA_FILE = os.path.join(BASE_DIR, "dashboard_data.js")

def clean_text(text):
    """HTML 태그, 엔티티 및 불필요한 줄바꿈/따옴표/공백을 깔끔하게 정리하는 함수"""
    if not text:
        return ""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', ' ', text)
    # HTML 특수문자 변환 (&amp; -> &, &quot; -> " 등)
    text = unescape(text)
    # 연속된 공백 및 줄바꿈 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_filename_meta(filename, rel_dir_path):
    """
    파일명과 상위 폴더 경로에서 기본 정보(연도, 월, 순번, 제목, 저자, 독서일자)를 추출합니다.
    파일명 예시: '1. 나를 비추는 작은 습관의 힘 (박훈)_20260901.html'
    """
    # 맥북의 NFD 한글을 표준 NFC로 정규화
    filename = unicodedata.normalize('NFC', filename)
    rel_dir_path = unicodedata.normalize('NFC', rel_dir_path)

    meta = {
        "title": "",
        "author": "",
        "read_date": "",
        "year": "기타",
        "month": "기타"
    }

    # 1. 파일명에서 독서일자 (_YYYYMMDD) 추출
    date_match = re.search(r'_(\d{8})\.html$', filename, re.IGNORECASE)
    if date_match:
        raw_date = date_match.group(1)
        meta["read_date"] = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        meta["year"] = raw_date[0:4]
        meta["month"] = f"{int(raw_date[4:6])}월"
    else:
        # 폴더 경로에서 연도와 월 유추 (예: '1. 2026/2. 9월')
        year_match = re.search(r'(\d{4})', rel_dir_path)
        if year_match:
            meta["year"] = year_match.group(1)
        month_match = re.search(r'(\d{1,2})월', rel_dir_path)
        if month_match:
            meta["month"] = f"{int(month_match.group(1))}월"

    # 2. 파일명에서 순번, 책 제목, 저자 추출
    name_without_ext = re.sub(r'_(\d{8})\.html$', '', filename, flags=re.IGNORECASE)
    name_without_ext = re.sub(r'\.html$', '', name_without_ext, flags=re.IGNORECASE)
    
    # 앞쪽 순번 제거 (예: '1. ', '2. ')
    name_without_order = re.sub(r'^\d+[\.\_\s]+', '', name_without_ext).strip()

    # 저자 괄호 탐색: '책제목 (저자이름)'
    author_match = re.search(r'^(.*?)\s*[\(\[\{]([^\)\]\}]+)[\)\]\}]$', name_without_order)
    if author_match:
        meta["title"] = author_match.group(1).strip()
        meta["author"] = author_match.group(2).strip()
    else:
        meta["title"] = name_without_order
        meta["author"] = "저자 미상"

    return meta

def extract_meta_from_html(file_path):
    """
    HTML 파일의 내용을 읽어 표지 이미지, 배지(장르/키워드), 인용구, 한줄평 등을 정밀 추출합니다.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ 파일 읽기 오류 ({file_path}): {e}")
        return {}

    extracted = {
        "cover_url": "",
        "badges": [],
        "quote": "",
        "one_line_review": "",
        "theme_color": "#1B263B",
        "accent_color": "#C5A880"
    }

    # 1. 테마 컬러 추출 (:root 내 --main-color, --accent-color 등)
    main_color_match = re.search(r'--main-color\s*:\s*([^;]+);', content)
    if main_color_match:
        extracted["theme_color"] = main_color_match.group(1).strip()

    accent_color_match = re.search(r'--accent-color\s*:\s*([^;]+);', content)
    if accent_color_match:
        extracted["accent_color"] = accent_color_match.group(1).strip()

    # 2. 표지 이미지(cover_url) 정밀 추출
    # 각 img 태그를 순회하면서 onerror가 아닌 실제 src 속성을 찾아냅니다.
    img_tags = re.findall(r'<img\b([^>]+)>', content, re.IGNORECASE | re.DOTALL)
    for tag_attrs in img_tags:
        # src 속성 추출
        src_match = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag_attrs, re.IGNORECASE)
        if src_match:
            candidate_src = src_match.group(1).strip()
            # placeholder 이미지는 실제 표지가 없을 때만 차순위로 고려
            if "placehold.co" not in candidate_src:
                extracted["cover_url"] = candidate_src
                break
            elif not extracted["cover_url"]:
                extracted["cover_url"] = candidate_src

    # 3. 배지 (장르 및 키워드 태그) 추출
    # 여러 디자인 패턴(badge, rounded-full 태그, hashtag 등)을 모두 수집
    badge_matches = re.findall(r'<span[^>]*class=["\'][^"\']*\bbadge\b[^"\']*["\'][^>]*>(.*?)</span>', content, re.DOTALL | re.IGNORECASE)
    tag_matches = re.findall(r'<span[^>]*class=["\'][^"\']*rounded-full[^"\']*["\'][^>]*>(.*?)</span>', content, re.DOTALL | re.IGNORECASE)
    hashtag_matches = re.findall(r'<span[^>]*class=["\'][^"\']*hashtag[^"\']*["\'][^>]*>(.*?)</span>', content, re.DOTALL | re.IGNORECASE)

    all_badges = badge_matches + tag_matches + hashtag_matches
    cleaned_badges = []
    # 제외할 UI 라벨 키워드
    excluded_labels = ["curator's note", "curator", "editorial critique", "fail_safe", "dynamic_theme", "editorial_design"]

    for b in all_badges:
        txt = clean_text(b).replace("#", "").strip()
        if txt and len(txt) <= 25 and txt.lower() not in excluded_labels:
            if txt not in cleaned_badges:
                cleaned_badges.append(txt)
    extracted["badges"] = cleaned_badges

    # 4. 핵심 인용구(The Core Quote) 정밀 추출
    # 4-1. 전용 클래스나 태그 우선 탐색 (core-quote 또는 quote-text)
    quote_match = re.search(r'<h[1-4][^>]*class=["\'][^"\']*(?:core-quote|quote-text)[^"\']*["\'][^>]*>(.*?)</h[1-4]>', content, re.DOTALL | re.IGNORECASE)
    if quote_match:
        extracted["quote"] = clean_text(quote_match.group(1))
    
    # 4-2. '<!-- 3. The Core Quote -->' 주석 섹션 내부 탐색
    if not extracted["quote"]:
        sec_quote_idx = content.find("<!-- 3. The Core Quote -->")
        if sec_quote_idx != -1:
            # 해당 섹션의 다음 1200자 내에서 주요 텍스트(p, h2, h3 등) 추출
            sec_snippet = content[sec_quote_idx:sec_quote_idx + 1200]
            # p 태그나 h 태그 중 내용이 있는 구문 탐색
            p_matches = re.findall(r'<(?:p|h[2-4])[^>]*>(.*?)</(?:p|h[2-4])>', sec_snippet, re.DOTALL | re.IGNORECASE)
            for p_text in p_matches:
                cleaned_p = clean_text(p_text).strip('"').strip('“').strip('”')
                if len(cleaned_p) >= 10: # 의미 있는 길이의 인용문
                    extracted["quote"] = cleaned_p
                    break

    # 5. 한 줄 서평(Curator's Note) 정밀 추출
    # 5-1. 전용 클래스 우선 탐색
    review_match = re.search(r'<h[1-4][^>]*class=["\'][^"\']*one-line-review[^"\']*["\'][^>]*>(.*?)</h[1-4]>', content, re.DOTALL | re.IGNORECASE)
    if review_match:
        extracted["one_line_review"] = clean_text(review_match.group(1))

    # 5-2. '<!-- 6. Curator\'s Note -->' 주석 섹션 내부 탐색
    if not extracted["one_line_review"]:
        sec_curator_idx = content.find("<!-- 6. Curator's Note -->")
        if sec_curator_idx != -1:
            sec_snippet = content[sec_curator_idx:sec_curator_idx + 1200]
            h_matches = re.findall(r'<(?:h[2-4]|p)[^>]*>(.*?)</(?:h[2-4]|p)>', sec_snippet, re.DOTALL | re.IGNORECASE)
            for h_text in h_matches:
                cleaned_h = clean_text(h_text).strip('"').strip('“').strip('”')
                if len(cleaned_h) >= 10 and "curator" not in cleaned_h.lower():
                    extracted["one_line_review"] = cleaned_h
                    break

    return extracted

def scan_all_books(base_dir):
    """
    기저 디렉토리의 모든 하위 폴더를 스캔하여 책 리뷰 HTML 파일 목록을 완성합니다.
    (단, index.html 및 시스템 가이드라인 HTML은 제외)
    """
    books = []
    
    for root, dirs, files in os.walk(base_dir):
        # 숨김 폴더나 시스템 관련 폴더 건너뛰기
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]

        for file in files:
            # HTML 파일만 대상
            if not file.lower().endswith(".html"):
                continue
            
            # 메인 대시보드 및 시스템 가이드라인 파일 제외
            lower_name = file.lower()
            if lower_name.startswith("index") or "guideline" in lower_name:
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, base_dir)
            rel_dir = os.path.relpath(root, base_dir)

            # 파일명 기반 기본 메타 추출
            file_meta = parse_filename_meta(file, rel_dir)

            # 본문 내용 기반 상세 메타 추출
            html_meta = extract_meta_from_html(full_path)

            # 도서 데이터 레코드 생성
            book_item = {
                "id": len(books) + 1,
                "title": file_meta["title"],
                "author": file_meta["author"],
                "read_date": file_meta["read_date"],
                "year": file_meta["year"],
                "month": file_meta["month"],
                "file_name": unicodedata.normalize('NFC', file),
                "relative_path": unicodedata.normalize('NFC', rel_path).replace("\\", "/"),
                "cover_url": html_meta.get("cover_url", ""),
                "badges": html_meta.get("badges", []),
                "quote": html_meta.get("quote", ""),
                "one_line_review": html_meta.get("one_line_review", ""),
                "theme_color": html_meta.get("theme_color", "#1B263B"),
                "accent_color": html_meta.get("accent_color", "#C5A880")
            }

            books.append(book_item)

    # 독서 일자 기준 최신순 정렬 (독서일자 없으면 파일명 역순)
    books.sort(key=lambda x: (x["read_date"], x["file_name"]), reverse=True)
    
    # 정렬 후 고유 순번(1부터 시작) 재부여
    for idx, b in enumerate(books, 1):
        b["id"] = idx

    return books

def compute_statistics(books):
    """
    수집된 도서 데이터를 바탕으로 대시보드에 바로 사용할 통계 지표를 계산합니다.
    """
    total_books = len(books)
    
    # 1. 연도별 통계 { "2026": 4, ... }
    year_counts = {}
    for b in books:
        y = b["year"]
        year_counts[y] = year_counts.get(y, 0) + 1

    # 2. 월별 통계 { "2026-08": 1, "2026-09": 3, ... }
    month_counts = {}
    for b in books:
        if b["read_date"]:
            ym = b["read_date"][:7] # YYYY-MM
            month_counts[ym] = month_counts.get(ym, 0) + 1
        else:
            ym = f"{b['year']}-{b['month']}"
            month_counts[ym] = month_counts.get(ym, 0) + 1

    # 월별 정렬
    sorted_months = sorted(month_counts.keys())
    monthly_trend = [{"month": m, "count": month_counts[m]} for m in sorted_months]

    # 3. 장르/키워드 빈도 집계
    genre_counts = {}
    for b in books:
        for badge in b["badges"]:
            genre_counts[badge] = genre_counts.get(badge, 0) + 1

    # 빈도수 순 정렬 상위 장르
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    top_genres = [{"genre": g, "count": c} for g, c in sorted_genres]

    # 4. 올해 독서 권수
    current_year = str(datetime.datetime.now().year)
    this_year_count = year_counts.get(current_year, 0)
    if this_year_count == 0 and year_counts:
        latest_year = max(year_counts.keys())
        this_year_count = year_counts[latest_year]
        current_year = latest_year

    return {
        "total_books": total_books,
        "current_year": current_year,
        "this_year_count": this_year_count,
        "year_counts": year_counts,
        "monthly_trend": monthly_trend,
        "top_genres": top_genres
    }

def main():
    print("=" * 65)
    print("📚 [북 리딩 로그 대시보드 데이터 빌더 시작]")
    print(f"📁 대상 탐색 폴더: {BASE_DIR}")
    print("=" * 65)

    # 1. 모든 도서 스캔
    books = scan_all_books(BASE_DIR)
    print(f"📖 총 {len(books)}권의 독서 리뷰 HTML 파일을 발견했습니다.\n")

    for b in books:
        cover_status = "✅ 표지확인" if b['cover_url'] else "❌ 표지없음"
        quote_status = "✅ 인용구있음" if b['quote'] else "⚪ 인용구없음"
        print(f"  [{b['id']}] {b['read_date']} | {b['title']} ({b['author']})")
        print(f"      상태: {cover_status} | {quote_status} | 배지({len(b['badges'])}개)")

    # 2. 통계 계산
    stats = compute_statistics(books)

    # 3. 데이터셋 패키징
    dashboard_payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "statistics": stats,
        "books": books
    }

    # 4. dashboard_data.js 로 저장
    js_content = f"// 자동 생성된 북 리딩 로그 데이터셋 ({dashboard_payload['generated_at']})\n"
    js_content += f"window.BOOK_DASHBOARD_DATA = {json.dumps(dashboard_payload, ensure_ascii=False, indent=2)};\n"

    with open(OUTPUT_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    print("\n" + "-" * 65)
    print(f"✅ 대시보드 데이터 파일이 성공적으로 생성되었습니다!")
    print(f"📄 저장 위치: {OUTPUT_DATA_FILE}")
    print(f"📊 총 도서: {stats['total_books']}권 | 올해 독서량: {stats['this_year_count']}권 | 분석된 키워드: {len(stats['top_genres'])}개")
    print("=" * 65)

if __name__ == "__main__":
    main()
