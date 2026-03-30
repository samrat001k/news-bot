import feedparser
import requests
import time
import schedule
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

NEWS_FEEDS = {
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
    "Prothom Alo":     "https://www.prothomalo.com/feed",
    "Daily Star":      "https://www.thedailystar.net/arcio/rss/",
    "Bdnews24":        "https://bdnews24.com/feed",
    "TehranTime":      "https://www.tehrantimes.com",
}

# কিওয়ার্ড ফিল্টার — এই শব্দ থাকলে Breaking News হিসেবে পাঠাবে
BREAKING_KEYWORDS = [
    "breaking", "urgent", "alert", "just in", "developing",
    "exclusive", "emergency", "crisis", "attack", "killed",
    "dead", "war", "explosion", "earthquake", "flood",
    "ব্রেকিং", "জরুরি", "হামলা", "নিহত", "বিস্ফোরণ"
]

# এই কিওয়ার্ড থাকলে নিউজ পাঠাবে — খালি রাখলে সব নিউজ পাঠাবে
FILTER_KEYWORDS = [
    # নির্দিষ্ট বিষয়ের নিউজ চাইলে এখানে লিখুন
    # যেমন: "Bangladesh", "AI", "technology", "economy"
    # এখন সব নিউজ আসবে
]

sent_links = set()
sent_titles = set()  # ডুপ্লিকেট চেক করতে
daily_news = []  # দিনের সেরা নিউজ জমা রাখতে

def gemini_request(prompt):
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error: " + str(e))
        return ""

def summarize_news(title, description):
    prompt = """Analyze this news and give me the key points in Bengali (Bangla) as bullet points.
Format exactly like this:
• [first key point in Bengali]
• [second key point in Bengali]
• [third key point in Bengali]

Only write the bullet points, nothing else. Maximum 3 bullets. Each bullet should be short (one line).

Title: """ + title + """
Description: """ + description
    result = gemini_request(prompt)
    if result:
        return result
    return "• " + (description[:100] if description else title)

def is_breaking(title, description):
    text = (title + " " + description).lower()
    for keyword in BREAKING_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False

def is_duplicate(title):
    # শিরোনামের প্রথম ৫০ অক্ষর মিলিয়ে দেখো
    short_title = title[:50].lower().strip()
    if short_title in sent_titles:
        return True
    sent_titles.add(short_title)
    return False

def should_include(title, description):
    if not FILTER_KEYWORDS:
        return True
    text = (title + " " + description).lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False

def send_telegram_text(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        return response.ok
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

def send_telegram_photo(image_url, caption):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        return response.ok
    except Exception as e:
        print("Photo send error: " + str(e))
        return False

def get_thumbnail(entry):
    # RSS থেকে ছবি খোঁজো
    try:
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0]['url']
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and any(ext in media['url'].lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    return media['url']
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href', '')
    except:
        pass
    return None

def send_news(category, title, summary, pub_date, link, image_url, breaking):
    if breaking:
        header = "🚨 <b>BREAKING NEWS</b> 🚨\n[" + category + "]\n━━━━━━━━━━━━━━━\n"
    else:
        header = "🔴 <b>[" + category + "]</b>\n━━━━━━━━━━━━━━━\n"

    caption = (
        header
        + "📌 <b>" + title + "</b>\n\n"
        + summary + "\n\n"
        + "🕐 " + (pub_date[:16] if pub_date else "") + "\n"
        + "🔗 <a href='" + link + "'>Read the full story</a>"
    )

    if image_url:
        success = send_telegram_photo(image_url, caption)
        if success:
            return True

    # ছবি না থাকলে বা ছবি পাঠাতে ব্যর্থ হলে টেক্সট পাঠাও
    return send_telegram_text(caption)

def check_new_news():
    global daily_news
    print("Checking for new news... " + datetime.now().strftime("%H:%M:%S"))
    new_count = 0

    for category, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in sent_links:
                    continue

                title = entry.get("title", "No title")
                description = entry.get("summary", "")
                pub_date = entry.get("published", "")

                # ডুপ্লিকেট চেক
                if is_duplicate(title):
                    sent_links.add(link)
                    continue

                # কিওয়ার্ড ফিল্টার
                if not should_include(title, description):
                    sent_links.add(link)
                    continue

                # Breaking News চেক
                breaking = is_breaking(title, description)

                # AI Summary
                summary = summarize_news(title, description)

                # থাম্বনেইল
                image_url = get_thumbnail(entry)

                # পাঠাও
                if send_news(category, title, summary, pub_date, link, image_url, breaking):
                    sent_links.add(link)
                    new_count += 1
                    # দিনের নিউজ লিস্টে যোগ করো
                    daily_news.append({
                        "title": title,
                        "category": category,
                        "summary": summary,
                        "link": link
                    })
                    print("Sent" + (" [BREAKING]" if breaking else "") + ": " + title[:50])
                    time.sleep(2)

        except Exception as e:
            print("Error in " + category + ": " + str(e))
            continue

    if new_count > 0:
        print(str(new_count) + " new news sent!")
    else:
        print("No new news.")

def send_daily_digest():
    global daily_news
    if not daily_news:
        return

    # সেরা ১০টা নিউজ নাও
    top_news = daily_news[-10:] if len(daily_news) > 10 else daily_news

    # Gemini দিয়ে দিনের সারসংক্ষেপ বানাও
    news_list = "\n".join([str(i+1) + ". " + n['title'] for i, n in enumerate(top_news)])
    prompt = "These are today's top news headlines. Write a brief Bengali summary of the day's most important events in 3-4 sentences:\n\n" + news_list
    digest_summary = gemini_request(prompt)

    message = (
        "🌙 <b>আজকের সেরা নিউজ সারসংক্ষেপ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + (digest_summary + "\n\n" if digest_summary else "")
        + "📋 <b>আজকের শীর্ষ খবর:</b>\n\n"
    )

    for i, news in enumerate(top_news):
        message += str(i+1) + ". <a href='" + news['link'] + "'>" + news['title'] + "</a>\n"

    message += "\n━━━━━━━━━━━━━━━━━━━━"
    send_telegram_text(message)

    # দিনের নিউজ রিসেট
    daily_news = []
    print("Daily digest sent!")

def load_existing_links():
    print("Loading existing news links...")
    for category, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "")
                if link:
                    sent_links.add(link)
                if title:
                    sent_titles.add(title[:50].lower().strip())
        except:
            continue
    print("Loaded " + str(len(sent_links)) + " existing links. Watching for NEW news...")

if __name__ == "__main__":
    print("News Bot starting...")
    load_existing_links()

    # প্রতি ৫ মিনিটে নতুন নিউজ চেক
    schedule.every(5).minutes.do(check_new_news)

    # প্রতিদিন রাত ১০টায় দিনের সেরা ১০ নিউজ সারসংক্ষেপ
    schedule.every().day.at("22:00").do(send_daily_digest)

    print("Bot running... Checking every 5 minutes.")
    while True:
        schedule.run_pending()
        time.sleep(30)
