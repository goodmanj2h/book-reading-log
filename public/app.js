// ==============================================================================
// 📖 독서 기록 대시보드 프론트엔드 컨트롤러 (app.js)
// - [하이브리드 지원] Mac 로컬 실시간 SSE 스트림 & GitHub Pages 24시간 클라우드 정적 모드
// - 웹 & 모바일 완벽 반응형, 실시간 도서 검색 및 인앱 슬라이드 뷰어 모달 제어
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. DOM 주요 요소 참조
// ------------------------------------------------------------------------------
const totalBooksEl = document.getElementById('totalBooks');
const booksThisYearEl = document.getElementById('booksThisYear');
const booksThisMonthEl = document.getElementById('booksThisMonth');
const currentYearLabel = document.getElementById('currentYearLabel');
const recentBooksList = document.getElementById('recentBooksList');
const bookGallery = document.getElementById('bookGallery');
const galleryCount = document.getElementById('galleryCount');
const tagFilters = document.getElementById('tagFilters');
const yearSelector = document.getElementById('yearSelector');

// 검색 관련 DOM 요소
const searchInput = document.getElementById('searchInput');
const searchClearBtn = document.getElementById('searchClearBtn');

// 상태 표시기 요소 (데스크톱 및 모바일)
const connectionStatus = document.getElementById('connectionStatus');
const statusIndicator = connectionStatus.querySelector('.status-indicator');
const statusText = connectionStatus.querySelector('span');
const mobileStatusBadge = document.getElementById('mobileStatusBadge');

// 인앱 독서록 모달 뷰어 요소
const bookViewerModal = document.getElementById('bookViewerModal');
const bookModalTitle = document.getElementById('bookModalTitle');
const bookViewerFrame = document.getElementById('bookViewerFrame');

// ------------------------------------------------------------------------------
// 2. 전역 상태 (State) 및 환경 감지
// ------------------------------------------------------------------------------
// 접속 환경 감지: 깃허브 페이지스(github.io)인지 로컬 서버(localhost / 127.0.0.1 등)인지 판별
const isGitHubPages = window.location.hostname.includes('github.io');

let allBooks = [];                 // 서버 또는 클라우드에서 받아온 전체 독서록 배열
let filteredBooks = [];            // 검색어나 태그 필터가 적용된 도서 배열
let chartInstance = null;          // Chart.js 인스턴스
let currentTagFilter = 'All';      // 현재 선택된 태그 ('All' = 전체)
let currentSearchKeyword = '';     // 현재 입력된 검색 키워드
let currentYearSelect = new Date().getFullYear(); // 통계 차트 선택 연도
let activeBook = null;             // 현재 모달에서 열람 중인 도서 객체

// ------------------------------------------------------------------------------
// 3. 상태 표시기 업데이트 헬퍼
// ------------------------------------------------------------------------------
const updateStatusUI = (isConnected, text) => {
    if (isConnected) {
        statusIndicator.classList.add('connected');
        statusText.textContent = text;
        if (mobileStatusBadge) {
            mobileStatusBadge.style.opacity = '1';
            const label = mobileStatusBadge.querySelector('.status-label');
            if (label) label.textContent = text;
        }
    } else {
        statusIndicator.classList.remove('connected');
        statusText.textContent = text;
        if (mobileStatusBadge) {
            mobileStatusBadge.style.opacity = '0.5';
            const label = mobileStatusBadge.querySelector('.status-label');
            if (label) label.textContent = text;
        }
    }
};

// ------------------------------------------------------------------------------
// 4. 데이터 로드 로직 (로컬 실시간 SSE + GitHub Pages 정적 클라우드)
// ------------------------------------------------------------------------------
// 4-1. GitHub Pages 정적 데이터(books_data.json) 로드
const fetchStaticData = async () => {
    try {
        const resp = await fetch('books_data.json?t=' + new Date().getTime());
        if (resp.ok) {
            const data = await resp.json();
            allBooks = data;
            updateDashboard();
            updateStatusUI(true, isGitHubPages ? '클라우드 연동됨' : '정적 데이터 로드');
            return true;
        }
    } catch (e) {
        console.warn('[알림] 정적 데이터 로드 실패:', e);
    }
    return false;
};

// 4-2. 로컬 파이썬 서버 실시간 동기화 (SSE: Server-Sent Events)
const connectSSE = () => {
    // 깃허브 페이지스 환경에서는 파이썬 서버가 없으므로 정적 파일만 읽고 종료
    if (isGitHubPages) {
        fetchStaticData();
        return;
    }

    const evtSource = new EventSource('/api/stream');
    
    evtSource.onopen = () => {
        updateStatusUI(true, '실시간 연동 중');
    };
    
    evtSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            allBooks = data;
            updateDashboard();
        } catch (error) {
            console.error('[오류] SSE 데이터 파싱 실패:', error);
        }
    };
    
    evtSource.onerror = async () => {
        evtSource.close();
        // SSE 연결이 안 될 경우 (예: 정적 모드 실행 시) books_data.json 폴백 시도
        const loaded = await fetchStaticData();
        if (!loaded) {
            updateStatusUI(false, '연결 끊김 (재시도 중...)');
        }
        // 5초 후 자동으로 재연결을 시도합니다.
        setTimeout(connectSSE, 5000);
    };
};

// 페이지 로드 시 환경에 맞추어 시작
if (isGitHubPages) {
    fetchStaticData();
} else {
    connectSSE();
}

// ------------------------------------------------------------------------------
// 5. 대시보드 화면 전체 갱신 함수
// ------------------------------------------------------------------------------
const updateDashboard = () => {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    if (currentYearLabel) {
        currentYearLabel.textContent = currentYear;
    }
    
    // [통계 계산]
    const total = allBooks.length;
    const thisYear = allBooks.filter(b => b.year === currentYear).length;
    const thisMonth = allBooks.filter(b => b.year === currentYear && b.month === currentMonth).length;
    
    // 부드러운 숫자 카운팅 애니메이션 실행
    animateValue(totalBooksEl, parseInt(totalBooksEl.textContent) || 0, total, 800);
    animateValue(booksThisYearEl, parseInt(booksThisYearEl.textContent) || 0, thisYear, 800);
    animateValue(booksThisMonthEl, parseInt(booksThisMonthEl.textContent) || 0, thisMonth, 800);
    
    // 최근 읽은 책 (상위 5권) 렌더링
    renderRecentBooks();
    
    // 월별 독서 추이 차트 갱신
    renderChart(currentYearSelect);
    
    // 태그 목록 갱신
    renderTags();
    
    // 갤러리 도서 렌더링 (검색 및 태그 필터 반영)
    applyFilterAndRender();
};

// ------------------------------------------------------------------------------
// 6. 숫자 애니메이션 헬퍼
// ------------------------------------------------------------------------------
const animateValue = (element, start, end, duration) => {
    if (!element) return;
    if (start === end) {
        element.innerHTML = end;
        return;
    }
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        element.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.innerHTML = end;
        }
    };
    window.requestAnimationFrame(step);
};

// ------------------------------------------------------------------------------
// 7. 도서 열람용 URL 생성 (로컬 API vs GitHub Pages 상대경로)
// ------------------------------------------------------------------------------
const getBookUrl = (bookId) => {
    // 깃허브 페이지스이거나 파일 프로토콜인 경우 정적 상대 경로를 URL 인코딩하여 직접 연결
    if (isGitHubPages || window.location.protocol === 'file:') {
        return encodeURI(bookId);
    }
    // 로컬 서버 환경에서는 보안 API 엔드포인트 사용
    return `/api/book?path=${encodeURIComponent(bookId)}`;
};

// ------------------------------------------------------------------------------
// 8. 최근 읽은 책 (Recent Books) 렌더링
// ------------------------------------------------------------------------------
const renderRecentBooks = () => {
    if (!recentBooksList) return;
    
    if (allBooks.length === 0) {
        recentBooksList.innerHTML = '<div class="loading-state"><p>등록된 독서 기록이 없습니다.</p></div>';
        return;
    }
    
    // 최근 5권 선택
    const recent = allBooks.slice(0, 5);
    recentBooksList.innerHTML = recent.map((book, idx) => {
        const publisherHtml = book.publisher ? `<span class="book-list-divider">|</span><span class="book-list-publisher">${book.publisher}</span>` : '';
        const genreText = book.tags && book.tags.length > 0 ? book.tags[0] : '';
        const genreHtml = genreText ? `<span class="book-list-divider">|</span><span class="book-list-genre">#${genreText}</span>` : '';
        
        return `
        <div class="book-list-item animate-fade" style="animation-delay: ${idx * 0.05}s" onclick="openBookModal('${encodeURIComponent(JSON.stringify(book))}')">
            <img src="${book.cover_url}" alt="${book.title}" class="book-thumb" onerror="this.src='https://placehold.co/400x600/F5F5F7/86868B?text=No+Cover'">
            <div class="book-list-info">
                <div class="book-list-title">${book.title}</div>
                <div class="book-list-meta">
                    <span class="book-list-author">${book.author}</span>
                    ${publisherHtml}
                    ${genreHtml}
                </div>
            </div>
        </div>
    `}).join('');
};

// ------------------------------------------------------------------------------
// 9. 태그 목록 렌더링 및 필터링
// ------------------------------------------------------------------------------
const renderTags = () => {
    if (!tagFilters) return;
    
    // 모든 책에서 고유한 태그 목록 수집
    const tagsSet = new Set();
    allBooks.forEach(b => {
        if (b.tags && Array.isArray(b.tags)) {
            b.tags.forEach(t => tagsSet.add(t));
        }
    });
    
    const tags = Array.from(tagsSet).sort();
    
    tagFilters.innerHTML = `
        <button class="pill ${currentTagFilter === 'All' ? 'active' : ''}" onclick="setTagFilter('All')">전체</button>
        ${tags.map(t => `
            <button class="pill ${currentTagFilter === t ? 'active' : ''}" onclick="setTagFilter('${t}')">#${t}</button>
        `).join('')}
    `;
};

window.setTagFilter = (tag) => {
    currentTagFilter = tag;
    renderTags();
    applyFilterAndRender();
};

// ------------------------------------------------------------------------------
// 10. 도서 검색 및 필터링 로직
// ------------------------------------------------------------------------------
const applyFilterAndRender = () => {
    let result = allBooks;
    
    // 1) 태그 필터 적용
    if (currentTagFilter !== 'All') {
        result = result.filter(b => b.tags && b.tags.includes(currentTagFilter));
    }
    
    // 2) 검색 키워드 필터 적용
    if (currentSearchKeyword.trim() !== '') {
        const keyword = currentSearchKeyword.toLowerCase().trim();
        result = result.filter(b => {
            const titleMatch = b.title && b.title.toLowerCase().includes(keyword);
            const authorMatch = b.author && b.author.toLowerCase().includes(keyword);
            const tagMatch = b.tags && b.tags.some(t => t.toLowerCase().includes(keyword));
            const publisherMatch = b.publisher && b.publisher.toLowerCase().includes(keyword);
            return titleMatch || authorMatch || tagMatch || publisherMatch;
        });
    }
    
    filteredBooks = result;
    
    if (galleryCount) {
        galleryCount.textContent = `${filteredBooks.length}권`;
    }
    
    renderGallery();
};

// 검색창 입력 이벤트 리스너
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        currentSearchKeyword = e.target.value;
        if (searchClearBtn) {
            searchClearBtn.classList.toggle('visible', currentSearchKeyword.length > 0);
        }
        applyFilterAndRender();
    });
}

if (searchClearBtn) {
    searchClearBtn.addEventListener('click', () => {
        searchInput.value = '';
        currentSearchKeyword = '';
        searchClearBtn.classList.remove('visible');
        applyFilterAndRender();
        searchInput.focus();
    });
}

// ------------------------------------------------------------------------------
// 11. 독서 갤러리 렌더링
// ------------------------------------------------------------------------------
const renderGallery = () => {
    if (!bookGallery) return;
    
    if (filteredBooks.length === 0) {
        bookGallery.innerHTML = `
            <div class="loading-state" style="grid-column: 1/-1">
                <p>일치하는 도서가 없습니다.</p>
            </div>
        `;
        return;
    }
    
    bookGallery.innerHTML = filteredBooks.map((book, idx) => `
        <div class="gallery-card animate-fade" style="animation-delay: ${(idx % 12) * 0.04}s" onclick="openBookModal('${encodeURIComponent(JSON.stringify(book))}')">
            <div class="gallery-cover-wrapper">
                <img src="${book.cover_url}" alt="${book.title}" class="gallery-cover" loading="lazy" onerror="this.src='https://placehold.co/400x600/F5F5F7/86868B?text=No+Cover'">
            </div>
            <div class="gallery-card-info">
                <div class="gallery-card-title">${book.title}</div>
                <div class="gallery-card-author">${book.author}</div>
            </div>
        </div>
    `).join('');
};

// ------------------------------------------------------------------------------
// 12. 인앱 독서록 뷰어 모달 (Modal Viewer) 제어
// ------------------------------------------------------------------------------
window.openBookModal = (encodedBookData) => {
    try {
        const book = JSON.parse(decodeURIComponent(encodedBookData));
        activeBook = book;
        
        bookModalTitle.textContent = book.title;
        // 환경에 맞는 안전한 독서록 URL 전달
        bookViewerFrame.src = getBookUrl(book.id);
        
        // 모달 표시
        bookViewerModal.classList.add('active');
        bookViewerModal.setAttribute('aria-hidden', 'false');
        
        // 뒷배경 스크롤 방지
        document.body.style.overflow = 'hidden';
    } catch (e) {
        console.error('[오류] 도서 모달 열기 실패:', e);
    }
};

window.closeBookModal = () => {
    bookViewerModal.classList.remove('active');
    bookViewerModal.setAttribute('aria-hidden', 'true');
    bookViewerFrame.src = 'about:blank';
    activeBook = null;
    document.body.style.overflow = '';
};

window.openCurrentBookInNewTab = () => {
    if (activeBook && activeBook.id) {
        window.open(getBookUrl(activeBook.id), '_blank');
    }
};

// ESC 키 입력 시 모달 닫기
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && bookViewerModal.classList.contains('active')) {
        closeBookModal();
    }
});

// ------------------------------------------------------------------------------
// 13. Chart.js 월별 독서 추이 차트
// ------------------------------------------------------------------------------
if (yearSelector) {
    yearSelector.addEventListener('change', (e) => {
        currentYearSelect = parseInt(e.target.value);
        renderChart(currentYearSelect);
    });
}

const renderChart = (year) => {
    const chartCanvas = document.getElementById('monthlyChart');
    if (!chartCanvas) return;
    
    const monthlyData = new Array(12).fill(0);
    
    // 등록된 책들에서 존재하는 모든 연도 추출
    const years = new Set(allBooks.map(b => b.year));
    years.add(new Date().getFullYear()); // 현재 연도는 항상 포함
    const sortedYears = Array.from(years).sort((a,b) => b-a);
    
    // 연도 셀렉트 드롭다운 갱신
    if (yearSelector && yearSelector.options.length !== sortedYears.length) {
        yearSelector.innerHTML = sortedYears.map(y => `<option value="${y}" ${y === currentYearSelect ? 'selected' : ''}>${y}년</option>`).join('');
    }
    
    // 선택된 연도의 월별 권수 집계
    allBooks.forEach(b => {
        if (b.year === year && b.month >= 1 && b.month <= 12) {
            monthlyData[b.month - 1]++;
        }
    });
    
    const ctx = chartCanvas.getContext('2d');
    
    // 애플 블루 그라데이션 영역 채우기 효과 생성
    const gradient = ctx.createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(0, 113, 227, 0.35)');
    gradient.addColorStop(1, 'rgba(0, 113, 227, 0.0)');
    
    if (chartInstance) {
        chartInstance.data.datasets[0].data = monthlyData;
        chartInstance.update();
    } else {
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
                datasets: [{
                    label: '완독한 책',
                    data: monthlyData,
                    borderColor: '#0071E3',
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    pointBackgroundColor: '#0071E3',
                    pointBorderColor: '#FFFFFF',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.35 // 부드러운 곡선
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(29, 29, 31, 0.9)',
                        titleFont: { family: 'Pretendard Variable', size: 12 },
                        bodyFont: { family: 'Pretendard Variable', size: 13, weight: 'bold' },
                        padding: 10,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            label: (context) => `읽은 책: ${context.parsed.y}권`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#86868B',
                            font: { family: 'Pretendard Variable', size: 11, weight: 500 }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.04)',
                            drawBorder: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#86868B',
                            font: { family: 'Pretendard Variable', size: 11, weight: 500 }
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
            }
        });
    }
};

// ------------------------------------------------------------------------------
// 14. 모바일 하단 네비게이션 및 스크롤 헬퍼
// ------------------------------------------------------------------------------
window.scrollToSection = (sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
    }
    
    // 하단 탭바 활성화 상태 변경
    document.querySelectorAll('.bottom-nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    const clickedBtn = event ? event.currentTarget : null;
    if (clickedBtn && clickedBtn.classList.contains('bottom-nav-item')) {
        clickedBtn.classList.add('active');
    }
};

window.focusSearch = () => {
    if (searchInput) {
        searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => searchInput.focus(), 300);
    }
};
