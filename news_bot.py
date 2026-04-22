import feedparser
import requests
import os
import json
from datetime import datetime, timedelta

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# 키워드 파일 읽기
with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip() for line in f if line.strip()]

# 이미 보낸 링크 목록 읽기
SENT_FILE = "sent_links.txt"
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
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def save_to_db(keyword, title, link):
    db_file = "news_db.json"
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = []
    db.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "keyword": keyword,
        "title": title,
        "link": link
    })
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_articles_by_date(keyword, date_str):
    db_file = "news_db.json"
    if not os.path.exists(db_file):
        return []
    with open(db_file, "r", encoding="utf-8") as f:
        db = json.load(f)
    return [a for a in db if a["keyword"] == keyword and a["date"] == date_str]

def analyze_with_gemini(keyword, today_articles, yesterday_articles):
    today_text = "\n".join([f"- {a['title']}" for a in today_articles]) or "없음"
    yesterday_text = "\n".join([f"- {a['title']}" for a in yesterday_articles]) or "없음"

    prompt = f"""당신은 뉴스 분석 전문가입니다.
아래는 '{keyword}' 키워드의 어제와 오늘 뉴스입니다.

[어제 뉴스]
{yesterday_text}

[오늘 뉴스]
{today_text}

다음 형식으로 분석해주세요 (각 항목 1-2줄):
📌 핵심 변화
📈 새로 생긴 이슈
📉 사라진 이슈
📋 변화 없는 것
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body)
    data = res.json()
    if "candidates" in data:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        print("Gemini 오류:", data)
        return "분석 실패"

# 날짜
today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

new_links = []

for keyword in keywords:
    articles = get_news(keyword)
    new_articles = [a for a in articles if a.link not in sent_links]

    if not new_articles:
        print(f"{keyword} - 새 기사 없음")
        continue

    # DB 저장
    for article in new_articles[:5]:
        save_to_db(keyword, article.title, article.link)
        new_links.append(article.link)

    # Gemini 분석
    today_db = get_articles_by_date(keyword, today)
    yesterday_db = get_articles_by_date(keyword, yesterday)
    analysis = analyze_with_gemini(keyword, today_db, yesterday_db)

    # 메시지 구성
    today_str = datetime.now().strftime("%Y-%m-%d")
    message = f"*[{keyword} 일일 분석] {today_str}*\n\n"
    message += analysis
    message += f"\n\n🔗 *근거 기사*\n"
    for i, article in enumerate(new_articles[:5], 1):
        message += f"{i}. {article.title}\n{article.link}\n"

    send_telegram(message)
    print(f"{keyword} 전송 완료")

# 새로 보낸 링크 저장
if new_links:
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        for link in new_links:
            f.write(link + "\n")
