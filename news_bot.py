import feedparser
import requests
import time
import schedule
import os

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
}

sent_links = set()

def summarize_news(title, description):
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
        prompt = """Analyze this news and give me the key points in Bengali (Bangla) as bullet points.
Format exactly like this:
• [first key point in Bengali]
• [second key point in Bengali]
• [third key point in Bengali]

Only write the bullet points, nothing else. Maximum 3 bullets. Each bullet should be short (one line).

Title: """ + title + """
Description: """ + description
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error: " + str(e))
        return "• " + (description[:100] if description else title)

def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
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
        print("Telegram error: " + str(e))
        return False

def check_new_news():
    print("Checking for new news...")
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

                summary = summarize_news(title, description)

                message = (
                    "🔴 <b>[" + category + "]</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "📌 <b>" + title + "</b>\n\n"
                    + summary + "\n\n"
                    + "🕐 " + (pub_date[:16] if pub_date else "") + "\n"
                    + "🔗 <a href='" + link + "'>পুরো খবর পড়ুন</a>"
                )

                if send_telegram(message):
                    sent_links.add(link)
                    new_count += 1
                    print("Sent: " + title[:50])
                    time.sleep(2)

        except Exception as e:
            print("Error in " + category + ": " + str(e))
            continue

    if new_count > 0:
        print(str(new_count) + " new news sent!")
    else:
        print("No new news found.")

def load_existing_links():
    print("Loading existing news links...")
    for category, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link:
                    sent_links.add(link)
        except:
            continue
    print("Loaded " + str(len(sent_links)) + " existing links. Watching for NEW news...")

if __name__ == "__main__":
    print("News Bot starting...")
    load_existing_links()
    # startup message removed
    schedule.every(5).minutes.do(check_new_news)
    print("Bot running... Checking every 5 minutes.")
    while True:
        schedule.run_pending()
        time.sleep(30)
