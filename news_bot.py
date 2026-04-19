import feedparser
import requests
import os

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

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
    return feed.entries[:10]  # 여유있게 10개 가져오기

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

new_links = []

for keyword in keywords:
    articles = get_news(keyword)

    new_articles = [a for a in articles if a.link not in sent_links]

    if not new_articles:
        print(f"{keyword} - 새 기사 없음")
        continue

    message = f"*[{keyword} 뉴스]*\n\n"
    for i, article in enumerate(new_articles[:5], 1):
        message += f"{i}. {article.title}\n{article.link}\n\n"
        new_links.append(article.link)

    send_telegram(message)
    print(f"{keyword} 전송 완료")

# 새로 보낸 링크 저장
if new_links:
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        for link in new_links:
            f.write(link + "\n")
