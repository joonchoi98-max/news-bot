import feedparser
import requests

TOKEN = "TELEGRAM_TOKEN_REMOVED"
CHAT_ID = "CHAT_ID_REMOVED"

# 키워드 파일에서 읽어오기
with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip() for line in f if line.strip()]

def get_news(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    return feed.entries[:5]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

for keyword in keywords:
    articles = get_news(keyword)
    
    message = f"*[{keyword} 뉴스]*\n\n"
    for i, article in enumerate(articles, 1):
        message += f"{i}. {article.title}\n{article.link}\n\n"
    
    send_telegram(message)
    print(f"{keyword} 전송 완료")