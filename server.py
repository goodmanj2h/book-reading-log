import http.server
import socketserver
import os
import time
import json
import re
import socket
import threading
import ssl
import unicodedata
import urllib.request
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ==============================================================================
# [환경 설정 및 상수]
# ==============================================================================
PORT = 3000

# 프로젝트의 현재 절대 경로를 자동으로 감지합니다.
# 이렇게 설정하면 폴더를 다른 위치나 컴퓨터로 옮겨도 경로 수정 없이 바로 작동합니다.
BASE_DIR = Path(__file__).resolve().parent

# 독서록 파일들이 저장되어 있는 디렉토리 (프로젝트 루트 디렉토리 기준)
BOOK_LOG_DIR = BASE_DIR

# 예스24(Yes24)에서 크롤링한 도서 정보(표지 이미지, 저자, 출판사)를 저장하는 캐시 파일
BOOK_CACHE_FILE = BASE_DIR / "book_cache.json"

# GitHub Pages 등 정적 클라우드 호스팅에서 사용되는 정적 JSON 데이터 파일
BOOKS_DATA_FILE = BASE_DIR / "books_data.json"

# ==============================================================================
# [전역 상태 변수]
# ==============================================================================
books_data = []         # 전체 독서록 목록 데이터 (JSON 변환용)
last_scan_time = 0      # 마지막 디렉토리 스캔 시간
sse_clients = []        # 실시간 변경 감지(SSE)를 구독 중인 웹 브라우저 클라이언트 목록
book_cache = {}         # 도서 메타데이터 메모리 캐시

# ==============================================================================
# [캐시 관리 함수]
# ==============================================================================
# 기존에 저장된 캐시 파일이 있다면 불러옵니다.
if BOOK_CACHE_FILE.exists():
    try:
        with open(BOOK_CACHE_FILE, 'r', encoding='utf-8') as f:
            book_cache = json.load(f)
    except Exception as e:
        print(f"[알림] 캐시 파일 로드 실패 (새로 생성합니다): {e}")
        book_cache = {}

def save_cache():
    """예스24에서 수집한 메타데이터를 캐시 파일에 영구 저장합니다."""
    try:
        with open(BOOK_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(book_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[오류] 캐시 파일 저장 실패: {e}")

# ==============================================================================
# [네트워크 유틸리티: 로컬 IP 확인]
# ==============================================================================
def get_local_ip():
    """스마트폰과 같은 Wi-Fi 망에서 접속할 수 있도록 Mac의 로컬 IP 주소를 조회합니다."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 외부 통신을 시도하여 현재 사용 중인 네트워크 인터페이스의 IP를 알아냅니다 (실제 패킷 전송 X)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ==============================================================================
# [Yes24 도서 정보 웹 스크래핑]
# ==============================================================================
def fetch_yes24_metadata(title):
    """
    책 제목을 기반으로 예스24(Yes24)에서 도서 표지, 저자, 출판사 정보를 자동으로 검색해 옵니다.
    이미 캐시에 존재하는 도서라면 웹 요청 없이 캐시된 정보를 즉시 반환하여 속도를 높입니다.
    """
    if title in book_cache:
        return book_cache[title]
        
    print(f"[Yes24 검색 중] {title}")
    # SSL 인증서 검증 우회 컨텍스트 생성 (로컬 개발 환경 호환성)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    query = urllib.parse.quote(title)
    url = f"https://www.yes24.com/Product/Search?domain=ALL&query={query}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    
    metadata = {
        "author": "작가 미상",
        "publisher": "",
        "cover_url": "https://placehold.co/400x600/F5F5F7/86868B?text=No+Cover"
    }
    
    try:
        html = urllib.request.urlopen(req, context=ctx, timeout=8).read().decode('utf-8', errors='ignore')
        img = re.search(r'<img[^>]+class="lazy"[^>]+data-original="([^"]+)"', html)
        author_match = re.search(r'<span class="authPub info_auth">.*?<a[^>]+>([^<]+)</a>', html, re.DOTALL)
        pub_match = re.search(r'<span class="authPub info_pub">.*?<a[^>]+>([^<]+)</a>', html, re.DOTALL)
        
        if img:
            metadata["cover_url"] = img.group(1)
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        if pub_match:
            metadata["publisher"] = pub_match.group(1).strip()
        
        # 검색된 결과를 메모리 캐시 및 파일에 저장
        book_cache[title] = metadata
        save_cache()
    except Exception as e:
        print(f"[알림] Yes24 검색 실패 ({title}): {e}")
        
    return metadata

# ==============================================================================
# [독서록 HTML 파일 파싱]
# ==============================================================================
def parse_html_file(file_path):
    """
    개별 독서록 HTML 파일을 읽어 제목, 저자, 태그(장르), 독서 날짜 등의 정보를 추출합니다.
    """
    try:
        path_obj = Path(file_path).resolve()
        with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 1. 제목 추출 (<title> 태그 우선, 없을 경우 h1/h2 태그에서 추출)
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).split('-')[0].split('|')[0].strip()
        else:
            t = re.search(r'<h[12][^>]*>(.*?)(?:<br>|</h[12]>)', content, re.IGNORECASE)
            title = re.sub(r'<[^>]+>', '', t.group(1)).strip() if t else path_obj.stem
            
        # 2. 태그 추출 (HTML 내의 #키워드 추출)
        tags = re.findall(r'<span[^>]*>#([^<]+)</span>', content)
        if not tags:
            # 본문 내의 해시태그 패턴 탐색
            tags = re.findall(r'#([가-힣a-zA-Z0-9_]+)', content)
            tags = list(dict.fromkeys([t for t in tags if len(t) <= 15]))[:5]
        
        # 3. 예스24 메타데이터 조회 (저자, 출판사, 표지 이미지)
        yes24_meta = fetch_yes24_metadata(title)
        author = yes24_meta.get("author", "작가 미상")
        publisher = yes24_meta.get("publisher", "")
        cover_url = yes24_meta.get("cover_url", "")

        # 4. 파일명에서 독서 완료 날짜 추출 (예: ..._20260905.html)
        date_match = re.search(r'_(\d{4})(\d{2})(\d{2})\.html$', path_obj.name)
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}-{month}-{day}"
        else:
            # 파일명에 날짜가 없다면 파일 최종 수정 시간 사용
            stat = path_obj.stat()
            date_str = time.strftime('%Y-%m-%d', time.localtime(stat.st_mtime))
            year, month, day = date_str.split('-')

        # 프로젝트 루트 기준 상대 경로 (웹 프론트엔드 통신 및 보안용)
        relative_path = str(path_obj.relative_to(BASE_DIR))

        return {
            "id": relative_path,           # 안전한 상대 경로 식별자
            "title": title,                 # 책 제목
            "author": author,               # 저자
            "publisher": publisher,         # 출판사
            "cover_url": cover_url,         # 표지 이미지 링크
            "tags": tags,                   # 태그/장르 목록
            "date": date_str,               # 독서 날짜 (YYYY-MM-DD)
            "year": int(year),              # 연도
            "month": int(month)             # 월
        }
    except Exception as e:
        print(f"[오류] 독서록 파일 파싱 실패 ({file_path}): {e}")
        return None

# ==============================================================================
# [디렉토리 전체 스캔 및 정적 JSON 자동 생성]
# ==============================================================================
def scan_directory():
    """
    프로젝트 디렉토리 내의 모든 독서록 HTML 파일을 탐색하고 목록을 갱신합니다.
    동시에 GitHub Pages 등 정적 호스팅을 위해 books_data.json 파일도 항상 최신화합니다.
    """
    global books_data, last_scan_time
    books = []
    
    if not BOOK_LOG_DIR.exists():
        print(f"[경고] 독서록 디렉토리가 존재하지 않습니다: {BOOK_LOG_DIR}")
        return False
        
    for root, dirs, files in os.walk(BOOK_LOG_DIR):
        root_path = Path(root)
        
        # 웹 프론트엔드 폴더(public)나 가상환경(venv), 캐시 폴더는 제외
        if any(part in ('public', 'venv', '__pycache__', '.git') for part in root_path.parts):
            continue
            
        for file in files:
            if file.endswith('.html'):
                # 메인 대시보드 파일(index.html), 서식 템플릿, 가이드 문서는 제외
                if file.lower() == "index.html" or "Guideline" in file or "Template" in file:
                    continue
                
                file_path = root_path / file
                book = parse_html_file(file_path)
                if book:
                    books.append(book)
                    
    # 최신 독서 날짜 순으로 내림차순 정렬
    books.sort(key=lambda x: x['date'], reverse=True)
    books_data = books
    last_scan_time = time.time()
    
    # [정적 클라우드 배포용 JSON 파일 자동 갱신]
    try:
        with open(BOOKS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(books_data, f, ensure_ascii=False, indent=2)
        # public 내부에도 복사본 유지
        public_data_file = BASE_DIR / "public" / "books_data.json"
        with open(public_data_file, 'w', encoding='utf-8') as f:
            json.dump(books_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[알림] 정적 데이터 파일 저장 오류: {e}")

    print(f"[스캔 완료] 총 {len(books_data)}권의 독서 기록을 로드했습니다.")
    return True

# ==============================================================================
# [실시간 SSE(Server-Sent Events) 브로드캐스트]
# ==============================================================================
def notify_clients():
    """새로운 독서록이 추가되거나 수정되면 연결된 모든 웹/모바일 브라우저에 즉시 전송합니다."""
    data = json.dumps(books_data, ensure_ascii=False)
    message = f"data: {data}\n\n"
    dead_clients = []
    for client in sse_clients:
        try:
            client.wfile.write(message.encode('utf-8'))
            client.wfile.flush()
        except Exception:
            dead_clients.append(client)
            
    for c in dead_clients:
        if c in sse_clients:
            sse_clients.remove(c)

def file_watcher():
    """
    백그라운드에서 독서록 폴더를 지속적으로 감시하여,
    HTML 파일이 추가되거나 변경되면 자동으로 다시 읽어 대시보드를 갱신합니다.
    """
    last_mod_time = 0
    while True:
        try:
            if BOOK_LOG_DIR.exists():
                current_mod_time = 0
                for root, dirs, files in os.walk(BOOK_LOG_DIR):
                    root_path = Path(root)
                    if any(part in ('public', 'venv', '__pycache__', '.git') for part in root_path.parts):
                        continue
                    mtime = root_path.stat().st_mtime
                    if mtime > current_mod_time:
                        current_mod_time = mtime
                    for file in files:
                        if file.endswith('.html') and file.lower() != 'index.html' and "Guideline" not in file and "Template" not in file:
                            fmtime = (root_path / file).stat().st_mtime
                            if fmtime > current_mod_time:
                                current_mod_time = fmtime

                if current_mod_time > last_mod_time:
                    if last_mod_time != 0:
                        print("[파일 변경 감지] 독서록을 다시 스캔합니다...")
                        if scan_directory():
                            notify_clients()
                    last_mod_time = current_mod_time
        except Exception as e:
            print(f"[감시 스레드 오류]: {e}")
        time.sleep(2)

# ==============================================================================
# [HTTP 요청 핸들러]
# ==============================================================================
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 정적 웹 파일은 프로젝트 루트 디렉토리에서 바로 서비스합니다 (GitHub Pages 호환 구조)
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # 1. 실시간 데이터 스트림 엔드포인트 (/api/stream)
        if parsed_path.path == '/api/stream':
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            sse_clients.append(self)
            
            # 최초 접속 시 현재 독서록 목록을 즉시 1회 전송합니다.
            try:
                data = json.dumps(books_data, ensure_ascii=False)
                self.wfile.write(f"data: {data}\n\n".encode('utf-8'))
                self.wfile.flush()
                while True:
                    time.sleep(1)
            except Exception:
                if self in sse_clients:
                    sse_clients.remove(self)
            return

        # 2. 독서록 원본 HTML 파일 제공 엔드포인트 (/api/book?path=...)
        if parsed_path.path == '/api/book':
            query = parse_qs(parsed_path.query)
            req_path = query.get('path', [''])[0]
            
            if not req_path:
                self.send_error(400, "Bad Request", explain="File path parameter is required.")
                return
                
            # [보안 검증 (Path Traversal 방지)]
            try:
                norm_path = unicodedata.normalize('NFC', req_path)
                candidate = Path(norm_path)
                
                if not candidate.is_absolute():
                    resolved_file = (BASE_DIR / candidate).resolve()
                else:
                    resolved_file = candidate.resolve()
                    
                # 만약 NFC 경로로 파일이 없으면 NFD로도 재시도
                if not resolved_file.exists():
                    nfd_path = unicodedata.normalize('NFD', req_path)
                    candidate_nfd = Path(nfd_path)
                    resolved_file = (BASE_DIR / candidate_nfd).resolve() if not candidate_nfd.is_absolute() else candidate_nfd.resolve()

                # 안전 검사: 파일이 프로젝트 폴더 내부에 위치하며, 실제 파일이고 확장자가 .html인지 확인
                is_safe = str(resolved_file).startswith(str(BASE_DIR)) and resolved_file.is_file() and resolved_file.suffix.lower() == '.html'
                
                # 기존 구버전 경로(/Users/jake/Desktop/Book Reading Log)로 들어온 경우도 안전하게 허용
                legacy_dir = Path("/Users/jake/Desktop/Book Reading Log").resolve()
                if not is_safe and str(resolved_file).startswith(str(legacy_dir)) and resolved_file.is_file() and resolved_file.suffix.lower() == '.html':
                    is_safe = True

                if is_safe and resolved_file.exists():
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    with open(resolved_file, 'r', encoding='utf-8', errors='ignore') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                    return
                else:
                    self.send_error(404, "File Not Found", explain="Book log file not found or access denied.")
                    return
            except Exception as e:
                self.send_error(500, "Internal Server Error", explain=f"Error reading file: {e}")
                return

        # 3. 그 외 기본 정적 파일(HTML, CSS, JS, JSON 등) 서빙
        return super().do_GET()
        
    def end_headers(self):
        # 브라우저 캐시 방지 헤더 (개발 및 실시간 반영 편의)
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    # 불필요한 콘솔 로그 억제 (깔끔한 터미널 출력 유지)
    def log_message(self, format, *args):
        pass

# ==============================================================================
# [메인 실행부]
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print(" 📖 독서 기록 대시보드 서버 (Book Reading Dashboard)")
    print("=" * 60)
    
    # 1. 초기 독서록 파일 스캔 및 books_data.json 자동 생성
    print("[1/2] 등록된 독서록 파일 스캔 중...")
    scan_directory()
    
    # 2. 파일 변경 감지 백그라운드 스레드 시작
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    print("[2/2] 독서록 실시간 감시 스레드 활성화 완료.")
    
    local_ip = get_local_ip()
    print("-" * 60)
    print(f" ▶ 로컬 접속 (PC 브라우저)   : http://localhost:{PORT}")
    print(f" ▶ 모바일 접속 (동일 Wi-Fi)  : http://{local_ip}:{PORT}")
    print(f" ▶ 외부/모바일 접속 (ngrok)  : 실행 스크립트(.command) 참조")
    print(f" ▶ 24시간 스마트폰 클라우드   : https://goodmanj2h.github.io/book-reading-log/")
    print("-" * 60)
    print(" (서버를 종료하시려면 터미널 창에서 Ctrl + C를 누르세요.)")
    print("=" * 60)
    
    # 3. HTTP 서버 시작
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), RequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[알림] 대시보드 서버를 안전하게 종료합니다.")
