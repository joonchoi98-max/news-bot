import feedparser
import requests
import os
import json
import html as _html
from datetime import datetime, timedelta
from collections import defaultdict

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip() for line in f if line.strip()]

SENT_FILE = "sent_links.txt"
DB_FILE = "news_db.json"
ANALYSIS_FILE = "analysis_db.json"

REAL_ESTATE_KEYWORDS = {"부동산규제", "아파트실거래가", "부동산정책"}

if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        sent_links = set(line.strip() for line in f)
else:
    sent_links = set()


def get_news(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    return feed.entries[:10]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)


def save_to_db(keyword, title, link):
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = []
    db.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "keyword": keyword,
        "title": title,
        "link": link,
    })
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_articles_by_date(keyword, date_str):
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    return [a for a in db if a["keyword"] == keyword and a["date"] == date_str]


def load_analysis_db():
    if os.path.exists(ANALYSIS_FILE):
        with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_analysis(keyword, date_str, analysis_text):
    db = load_analysis_db()
    if keyword not in db:
        db[keyword] = {}
    db[keyword][date_str] = analysis_text
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _build_prompt(keyword, today_text, yesterday_text):
    header = f"""당신은 뉴스 분석 전문가입니다.
아래는 '{keyword}' 키워드의 어제와 오늘 뉴스입니다.

[어제 뉴스]
{yesterday_text}

[오늘 뉴스]
{today_text}

"""
    footer = "\n주의: 마크다운 기호(##, **, __ 등)는 절대 사용하지 마세요. 이모지와 일반 텍스트만 사용하세요.\n"

    if keyword in REAL_ESTATE_KEYWORDS:
        body = """다음 3가지 관점으로 분석해주세요 (각 항목 1-2줄):
🏛 정책변화: 최근 정부/지자체 부동산 정책 변화
📊 가격동향: 아파트, 전세 등 가격 흐름
💰 투자시사점: 위 내용을 종합한 시장 시사점"""
    else:
        body = """다음 3가지 항목으로 분석해주세요 (각 항목 1-2줄):
📌 핵심 변화: 어제 대비 오늘 달라진 핵심 흐름
📈 새로 부상한 이슈: 오늘 처음 등장한 주제나 사건
💡 주목 포인트: 앞으로 지켜봐야 할 한 가지 포인트"""

    return header + body + footer


def analyze_with_gemini(keyword, today_articles, yesterday_articles):
    today_text = "\n".join([f"- {a['title']}" for a in today_articles]) or "없음"
    yesterday_text = "\n".join([f"- {a['title']}" for a in yesterday_articles]) or "없음"
    prompt = _build_prompt(keyword, today_text, yesterday_text)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body)
    data = res.json()
    if "candidates" in data:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    print("Gemini 오류:", data)
    return "분석 실패"


_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif; background: #f0f2f5; color: #1a1a2e; min-height: 100vh; }
    header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%); color: white; padding: 28px 32px; box-shadow: 0 2px 12px rgba(0,0,0,.3); }
    header h1 { font-size: 1.8rem; font-weight: 700; }
    header p { font-size: 0.83rem; color: #94a3b8; margin-top: 6px; }
    .container { max-width: 1100px; margin: 0 auto; padding: 28px 20px; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
    .tab-btn { padding: 10px 22px; border: 2px solid #e2e8f0; border-radius: 24px; background: white; color: #64748b; font-size: 0.93rem; font-weight: 600; cursor: pointer; transition: all .18s; }
    .tab-btn:hover { border-color: #818cf8; color: #818cf8; }
    .tab-btn.active { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-color: transparent; color: white; box-shadow: 0 4px 14px rgba(99,102,241,.35); }
    .analysis-box { background: #f5f3ff; border: 1px solid #c4b5fd; border-left: 4px solid #6366f1; border-radius: 12px; padding: 20px 24px; margin-bottom: 28px; }
    .analysis-title { font-size: 0.95rem; font-weight: 700; color: #4f46e5; margin-bottom: 10px; }
    .analysis-date { font-weight: 400; color: #9ca3af; font-size: 0.8rem; }
    .analysis-content { font-size: 0.88rem; line-height: 2; color: #374151; }
    .date-section { margin-bottom: 32px; }
    .date-header { font-size: 0.78rem; font-weight: 700; color: #6b7280; letter-spacing: 1px; text-transform: uppercase; padding-bottom: 8px; border-bottom: 2px solid #e5e7eb; margin-bottom: 14px; }
    .articles-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 12px; }
    .article-card { display: block; background: white; border-radius: 10px; padding: 16px 18px; text-decoration: none; color: inherit; border: 1px solid #f1f5f9; box-shadow: 0 1px 3px rgba(0,0,0,.06); transition: all .18s; }
    .article-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.1); border-color: #c7d2fe; }
    .article-title { font-size: 0.88rem; font-weight: 600; line-height: 1.55; color: #1e293b; margin-bottom: 10px; }
    .article-meta { font-size: 0.76rem; color: #6366f1; font-weight: 500; }
    .empty-msg { text-align: center; color: #9ca3af; padding: 60px 0; font-size: 0.95rem; }
    @media (max-width: 600px) {
      header { padding: 20px; }
      header h1 { font-size: 1.4rem; }
      .articles-grid { grid-template-columns: 1fr; }
    }
"""

_JS = """
    function showTab(idx) {
      document.querySelectorAll('.tab-content').forEach(function(el) { el.style.display = 'none'; });
      document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
      document.querySelectorAll('.tab-content')[idx].style.display = 'block';
      document.querySelectorAll('.tab-btn')[idx].classList.add('active');
    }
"""


def generate_html_dashboard():
    db = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)

    analysis_db = load_analysis_db()

    kw_date_articles = defaultdict(lambda: defaultdict(list))
    for article in db:
        kw_date_articles[article["keyword"]][article["date"]].append(article)

    all_keywords = [kw for kw in keywords if kw in kw_date_articles]
    for kw in kw_date_articles:
        if kw not in all_keywords:
            all_keywords.append(kw)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not all_keywords:
        body_html = '  <div class="container"><p class="empty-msg">아직 수집된 뉴스가 없습니다.</p></div>\n'
        inner = body_html
        tabs_html = ""
    else:
        tab_buttons_html = ""
        for i, kw in enumerate(all_keywords):
            active = " active" if i == 0 else ""
            tab_buttons_html += (
                f'      <button class="tab-btn{active}" onclick="showTab({i})">'
                f'{_html.escape(kw)}</button>\n'
            )

        tab_contents_html = ""
        for i, kw in enumerate(all_keywords):
            display = "block" if i == 0 else "none"
            dates = sorted(kw_date_articles[kw].keys(), reverse=True)

            analysis_section = ""
            if kw in analysis_db and analysis_db[kw]:
                latest_date = max(analysis_db[kw].keys())
                analysis_escaped = (
                    _html.escape(analysis_db[kw][latest_date]).replace("\n", "<br>")
                )
                analysis_section = (
                    '    <div class="analysis-box">\n'
                    '      <div class="analysis-title">🤖 Gemini AI 분석'
                    f' <span class="analysis-date">({_html.escape(latest_date)})</span></div>\n'
                    f'      <div class="analysis-content">{analysis_escaped}</div>\n'
                    '    </div>\n'
                )

            dates_html = ""
            for date in dates:
                articles = kw_date_articles[kw][date]
                cards_html = ""
                for article in articles:
                    cards_html += (
                        f'        <a href="{_html.escape(article["link"])}"'
                        ' target="_blank" rel="noopener" class="article-card">\n'
                        f'          <div class="article-title">{_html.escape(article["title"])}</div>\n'
                        '          <div class="article-meta">기사 보기 →</div>\n'
                        '        </a>\n'
                    )
                dates_html += (
                    '    <div class="date-section">\n'
                    f'      <div class="date-header">{_html.escape(date)}</div>\n'
                    '      <div class="articles-grid">\n'
                    + cards_html
                    + '      </div>\n'
                    '    </div>\n'
                )

            tab_contents_html += (
                f'  <div class="tab-content" style="display:{display}">\n'
                + analysis_section
                + dates_html
                + '  </div>\n'
            )

        tabs_html = (
            '    <div class="tabs">\n'
            + tab_buttons_html
            + '    </div>\n'
        )
        inner = tabs_html + tab_contents_html

    html_content = (
        '<!DOCTYPE html>\n'
        '<html lang="ko">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <title>뉴스 대시보드</title>\n'
        '  <style>' + _CSS + '  </style>\n'
        '</head>\n'
        '<body>\n'
        '  <header>\n'
        '    <h1>📰 뉴스 대시보드</h1>\n'
        f'    <p>마지막 업데이트: {generated_at} · Powered by Gemini AI</p>\n'
        '  </header>\n'
        '  <div class="container">\n'
        + inner
        + '  </div>\n'
        '  <script>' + _JS + '  </script>\n'
        '</body>\n'
        '</html>\n'
    )

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("HTML 대시보드 생성 완료: docs/index.html")


today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

new_links = []

for keyword in keywords:
    articles = get_news(keyword)
    new_articles = [a for a in articles if a.link not in sent_links]

    if not new_articles:
        print(f"{keyword} - 새 기사 없음")
        continue

    for article in new_articles[:5]:
        save_to_db(keyword, article.title, article.link)
        new_links.append(article.link)

    today_db = get_articles_by_date(keyword, today)
    yesterday_db = get_articles_by_date(keyword, yesterday)
    analysis = analyze_with_gemini(keyword, today_db, yesterday_db)

    save_analysis(keyword, today, analysis)

    today_str = datetime.now().strftime("%Y-%m-%d")
    message = f"<b>[{keyword} 일일 분석] {today_str}</b>\n\n"
    message += analysis
    message += f"\n\n🔗 <b>근거 기사</b>\n"
    for i, article in enumerate(new_articles[:5], 1):
        message += f'{i}. <a href="{article.link}">{article.title}</a>\n'

    send_telegram(message)
    print(f"{keyword} 전송 완료")

if new_links:
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        for link in new_links:
            f.write(link + "\n")

generate_html_dashboard()
