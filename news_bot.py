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

# আগে দেখা লিংক সেভ করে রাখবে — একই নিউজ দুইবার পাঠাবে না
sent_links = set()

def summarize_news(title, description):
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
        prompt = "Summarize this news in 2-3 sentences in Bengali (Bangla). Only write the summary, nothing else.\n\nTitle: " + title + "\nDescription: " + description
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error: " + str(e))
        return description[:200] if description else title

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

                # নতুন নিউজ পাওয়া গেছে!
                title = entry.get("title", "No title")
                description = entry.get("summary", "")
                pub_date = entry.get("published", "")

                summary = summarize_news(title, description)

                message = (
                    "🔴 <b>[" + category + "]</b>\n\n"
                    "<b>" + title + "</b>\n\n"
                    + summary + "\n\n"
                    + (pub_date[:16] if pub_date else "") + "\n"
                    + "<a href='" + link + "'>Read full news</a>"
                )

                if send_telegram(message):
                    sent_links.add(link)
                    new_count += 1
                    print("New news sent: " + title[:50])
                    time.sleep(2)

        except Exception as e:
            print("Error in " + category + ": " + str(e))
            continue

    if new_count > 0:
        print(str(new_count) + " new news sent!")
    else:
        print("No new news found.")

# প্রথমবার সব পুরনো লিংক লোড করো — পাঠাবে না, শুধু মনে রাখবে
def load_existing_links():
    print("Loading existing news links (will not send these)...")
    for category, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link:
                    sent_links.add(link)
        except:
            continue
    print("Loaded " + str(len(sent_links)) + " existing links. Now watching for NEW news...")

if __name__ == "__main__":
    print("News Bot starting...")

    # প্রথমে পুরনো নিউজ লোড করো যাতে পুরনো নিউজ না পাঠায়
    load_existing_links()
    send_telegram("✅ <b>News Bot চালু হয়েছে!</b> নতুন নিউজ আসলে সাথে সাথে পাঠাবো।")

    # প্রতি ৫ মিনিটে চেক করবে
    schedule.every(5).minutes.do(check_new_news)

    print("Bot running... Checking every 5 minutes for new news.")
    while True:
        schedule.run_pending()
        time.sleep(30)
