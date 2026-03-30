import feedparser
import requests
import time
import schedule
from anthropic import Anthropic

# ========================================
# আপনার তথ্য এখানে বসান
# ========================================
TELEGRAM_BOT_TOKEN = "আপনার_TELEGRAM_BOT_TOKEN"  # BotFather থেকে পাবেন
TELEGRAM_CHAT_ID = "আপনার_CHAT_ID"               # নিচে দেখুন কীভাবে পাবেন
ANTHROPIC_API_KEY = "আপনার_CLAUDE_API_KEY"        # console.anthropic.com থেকে পাবেন

# ========================================
# Google News RSS Feeds (বিষয় পরিবর্তন করতে পারেন)
# ========================================
NEWS_FEEDS = {
    "বাংলাদেশ": "https://news.google.com/rss/search?q=Bangladesh&hl=bn&gl=BD&ceid=BD:bn",
    "প্রযুক্তি": "https://news.google.com/rss/search?q=technology&hl=bn&gl=BD&ceid=BD:bn",
    "ব্যবসা":   "https://news.google.com/rss/search?q=business+Bangladesh&hl=bn&gl=BD&ceid=BD:bn",
}

# কতটা নিউজ পাঠাবে প্রতিবার
NEWS_PER_CATEGORY = 3

# ========================================
# Claude AI দিয়ে সারসংক্ষেপ বানানো
# ========================================
client = Anthropic()

def summarize_news(title, description):
    """Claude দিয়ে নিউজ সারসংক্ষেপ বানাও"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"""নিচের নিউজটি বাংলায় ২-৩ লাইনে সংক্ষেপ করো। 
শুধু মূল তথ্য রাখো, সহজ বাংলায় লেখো।

শিরোনাম: {title}
বিবরণ: {description}

শুধু সারসংক্ষেপ লেখো, অন্য কিছু না।"""
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        return description[:200] if description else title

# ========================================
# Telegram এ মেসেজ পাঠানো
# ========================================
def send_telegram(message):
    """Telegram Bot এ মেসেজ পাঠাও"""
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
sent_links = set()  # একই নিউজ দুইবার না পাঠাতে

def fetch_and_send_news():
    """Google News থেকে নিউজ নিয়ে Telegram এ পাঠাও"""
    print("নিউজ কালেক্ট করছি...")

    for category, feed_url in NEWS_FEEDS.items():
        feed = feedparser.parse(feed_url)
        count = 0

        # ক্যাটাগরি হেডার পাঠাও
        header = f"📰 <b>{'='*20}</b>\n🗂 <b>{category} নিউজ</b>\n<b>{'='*20}</b>"
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

            # AI দিয়ে সারসংক্ষেপ বানাও
            summary = summarize_news(title, description)

            # মেসেজ ফরম্যাট
            message = (
                f"📌 <b>{title}</b>\n\n"
                f"💬 {summary}\n\n"
                f"🕐 {pub_date[:16] if pub_date else 'তারিখ নেই'}\n"
                f"🔗 <a href='{link}'>পুরো খবর পড়ুন</a>"
            )

            if send_telegram(message):
                sent_links.add(link)
                count += 1
                print(f"✅ পাঠানো হয়েছে: {title[:50]}")
                time.sleep(2)  # Telegram rate limit এড়াতে

    send_telegram("✅ <b>সব নিউজ আপডেট শেষ!</b> পরবর্তী আপডেট ১ ঘন্টা পরে।")
    print("✅ সব নিউজ পাঠানো শেষ!")

# ========================================
# CHAT ID বের করার ফাংশন
# ========================================
def get_chat_id():
    """আপনার Chat ID বের করুন"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    data = response.json()
    if data["ok"] and data["result"]:
        chat_id = data["result"][-1]["message"]["chat"]["id"]
        print(f"✅ আপনার Chat ID: {chat_id}")
        return chat_id
    else:
        print("❌ আগে Bot কে একটা মেসেজ পাঠান, তারপর এটা চালান।")
        return None

# ========================================
# মেইন প্রোগ্রাম
# ========================================
if __name__ == "__main__":
    print("🤖 News Bot চালু হচ্ছে...")
    
    # প্রথমে Chat ID বের করুন (একবারের জন্য)
    # get_chat_id()  # এই লাইনের # সরিয়ে একবার চালান, ID পেলে আবার # দিন
    
    # প্রথমবার এখনই নিউজ পাঠাও
    fetch_and_send_news()
    
    # প্রতি ১ ঘন্টা পরপর অটো আপডেট
    schedule.every(1).hours.do(fetch_and_send_news)
    
    print("⏰ Bot চলছে... প্রতি ১ ঘন্টায় নিউজ আসবে। বন্ধ করতে Ctrl+C চাপুন।")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
