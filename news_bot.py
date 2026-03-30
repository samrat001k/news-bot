import feedparser
import requests
import time
import schedule
import os

# ========================================
# আপনার তথ্য এখানে বসান
# ========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "আপনার_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "আপনার_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "আপনার_GEMINI_API_KEY")

# ========================================
# RSS Feeds — World Top 10 + Bangladesh Top 3
# ========================================
NEWS_FEEDS = {
    # 🌍 বিশ্বের টপ ১০ নিউজ পোর্টাল
    "BBC News":        "http://feeds.bbci.co.uk/news/rss.xml",
    "Reuters":         "https://feeds.reuters.com/reuters/topNews",
    "Al Jazeera":      "https://www.aljazeera.com/xml/rss/all.xml",
    "CNN":             "http://rss.cnn.com/rss/edition.rss",
    "The Guardian":    "https://www.theguardian.com/world/rss",
    "NY Times":        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Washington Post": "https://feeds.washingtonpost.com/rss/world",
    "AP News":         "https://rsshub.app/apnews/topics/apf-topnews",
    "DW News":         "https://rss.dw.com/rdf/rss-en-all",
    "France 24":       "https://www.france24.com/en/rss",

    # 🇧🇩 বাংলাদেশের টপ ৩ নিউজ পোর্টাল
    "Prothom Alo":     "https://www.prothomalo.com/feed",
    "Daily Star":      "https://www.thedailystar.net/arcio/rss/",
    "Bdnews24":        "https://bdnews24.com/feed",
}

# প্রতিটা সাইট থেকে কতটা নিউজ পাঠাবে
NEWS_PER_CATEGORY = 2

# ========================================
# Gemini AI দিয়ে সারসংক্ষেপ বানানো
# ========================================
def summarize_news(title, description):
    """Gemini দিয়ে নিউজ বাংলায় সারসংক্ষেপ বানাও"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""নিচের নিউজটি বাংলায় ২-৩ লাইনে সংক্ষেপ করো।
শুধু মূল তথ্য রাখো, সহজ বাংলায় লেখো।

শিরোনাম: {title}
বিবরণ: {description}

শুধু সারসংক্ষেপ লেখো, অন্য কিছু না।"""
                }]
            }]
        }
        response = requests.post(url, json=payload)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini error: {e}")
        return description[:200] if description else title

# ========================================
# Telegram এ মেসেজ পাঠানো
# ========================================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        return response.ok
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# ========================================
# নিউজ কালেক্ট করা ও পাঠানো
# ========================================
sent_links = set()

def fetch_and_send_news():
    print("নিউজ কালেক্ট করছি...")

    send_telegram("🌐 <b>নিউজ আপডেট শুরু হচ্ছে...</b>")
    time.sleep(1)

    for category, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            count = 0

            header = f"📰 <b>── {category} ──</b>"
            send_telegram(header)
            time.sleep(1)

            for entry in feed.entries:
                if count >= NEWS_PER_CATEGORY:
                    break

                link = entry.get("link", "")
                if link in sent_links:
                    continue

                title = entry.get("title", "শিরোনাম নেই")
                description = entry.get("summary", "")
                pub_date = entry.get("published", "")

                summary = summarize_news(title, description)

                message = (
                    f"📌 <b>{title}</b>\n\n"
                    f"💬 {summary}\n\n"
                    f"🕐 {pub_date[:16] if pub_date else 'তারিখ নেই'}\n"
                    f"🔗 <a href='{link}'>পুরো খবর পড়ুন</a>"
                )

                if send_telegram(message):
                    sent_links.add(link)
                    count += 1
                    print(f"✅ [{category}] {title[:50]}")
                    time.sleep(2)

        except Exception as e:
            print(f"❌ {category} error: {e}")
            continue

    send_telegram("✅ <b>সব নিউজ আপডেট শেষ!</b> পরবর্তী আপডেট ১ ঘন্টা পরে।")
    print("✅ সব নিউজ পাঠানো শেষ!")

# ========================================
# মেইন প্রোগ্রাম
# ========================================
if __name__ == "__main__":
    print("🤖 News Bot চালু হচ্ছে...")
    fetch_and_send_news()

    schedule.every(0.01).hours.do(fetch_and_send_news)

    print("⏰ Bot চলছে... প্রতি ১ ঘন্টায় নিউজ আসবে।")

    while True:
        schedule.run_pending()
        time.sleep(60
