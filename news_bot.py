import requests
from bs4 import BeautifulSoup
import schedule
import time
import os
import json
import hashlib
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# =============================================
# সরকারি জব সাইটগুলো
# =============================================
JOB_SOURCES = [
    {
        "name": "বাংলাদেশ সরকারি কর্ম কমিশন (BPSC)",
        "url": "https://bpsc.gov.bd/site/view/notices",
        "emoji": "🏛️"
    },
    {
        "name": "বাংলাদেশ সরকারি পোর্টাল",
        "url": "https://bangladesh.gov.bd/site/view/job_circular",
        "emoji": "🇧🇩"
    },
    {
        "name": "প্রধানমন্ত্রীর কার্যালয়",
        "url": "https://pmo.gov.bd/site/view/job_circular",
        "emoji": "🏢"
    },
    {
        "name": "স্বাস্থ্য মন্ত্রণালয়",
        "url": "https://mohfw.gov.bd/site/view/notices",
        "emoji": "🏥"
    },
    {
        "name": "শিক্ষা মন্ত্রণালয়",
        "url": "https://moedu.gov.bd/site/view/notices",
        "emoji": "📚"
    },
    {
        "name": "অর্থ মন্ত্রণালয়",
        "url": "https://mof.gov.bd/site/view/notices",
        "emoji": "💰"
    },
    {
        "name": "স্বরাষ্ট্র মন্ত্রণালয়",
        "url": "https://moha.gov.bd/site/view/notices",
        "emoji": "🛡️"
    },
    {
        "name": "কৃষি মন্ত্রণালয়",
        "url": "https://moa.gov.bd/site/view/notices",
        "emoji": "🌾"
    },
    {
        "name": "তথ্য ও যোগাযোগ মন্ত্রণালয়",
        "url": "https://ictd.gov.bd/site/view/notices",
        "emoji": "💻"
    },
        {
        "name": "BDjobs Government",
        "url": "https://bdjobs.com/h/jobs?requestType=government",
        "emoji": "📋"
    },
    {
        "name": "BDjobs Government",
        "url": "https://www.bdjobs.com/jobssearched.asp?TypeJobs=2&AdType=1",
        "emoji": "📋"
    },
    {
        "name": "ejobsbd.com",
        "url": "https://ejobsbd.com/government-job/",
        "emoji": "📌"
    },
]

# =============================================
# পাঠানো জব ট্র্যাক করা
# =============================================
SENT_JOBS_FILE = "sent_jobs.json"

def load_sent_jobs():
    try:
        with open(SENT_JOBS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_sent_jobs(sent_jobs):
    with open(SENT_JOBS_FILE, "w") as f:
        json.dump(list(sent_jobs), f)

sent_jobs = load_sent_jobs()

def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

# =============================================
# Gemini দিয়ে জব বিজ্ঞপ্তি বিশ্লেষণ
# =============================================
def analyze_job(title, description):
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
        prompt = """এই সরকারি চাকরির বিজ্ঞপ্তিটি বিশ্লেষণ করো এবং বাংলায় নিচের ফরম্যাটে দাও:

• পদের নাম: [পদের নাম]
• মন্ত্রণালয়/দপ্তর: [নাম]
• পদ সংখ্যা: [সংখ্যা বা N/A]
• শেষ তারিখ: [তারিখ বা N/A]
• যোগ্যতা: [সংক্ষেপে]

শুধু এই ৫টা পয়েন্ট লেখো, অন্য কিছু না।

বিজ্ঞপ্তি: """ + title + " " + description
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return "• পদের নাম: " + title[:80]

# =============================================
# ওয়েবসাইট স্ক্র্যাপ করা
# =============================================
def scrape_jobs(source):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    jobs = []
    try:
        response = requests.get(source["url"], headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # সব লিংক খোঁজো যেগুলোতে চাকরি সংক্রান্ত কিওয়ার্ড আছে
        job_keywords = [
            'চাকরি', 'নিয়োগ', 'বিজ্ঞপ্তি', 'পদ', 'circular', 'job',
            'recruit', 'vacancy', 'নিয়োগ বিজ্ঞপ্তি', 'career'
        ]

        links = soup.find_all('a', href=True)
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')

            if len(title) < 10:
                continue

            # কিওয়ার্ড চেক
            title_lower = title.lower()
            if any(kw.lower() in title_lower for kw in job_keywords):
                full_url = href if href.startswith('http') else source["url"].split('/site')[0] + href
                job_id = make_id(title)
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "url": full_url,
                    "source": source["name"],
                    "emoji": source["emoji"]
                })

        # bdjobs এর জন্য আলাদা স্ক্র্যাপিং
        if 'bdjobs' in source["url"]:
            job_rows = soup.find_all('div', class_='job-title-text') or soup.find_all('a', class_='noUnderline')
            for row in job_rows[:10]:
                title = row.get_text(strip=True)
                href = row.get('href', '') if row.name == 'a' else ''
                if title and len(title) > 5:
                    job_id = make_id(title)
                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "url": href if href.startswith('http') else "https://bdjobs.com" + href,
                        "source": source["name"],
                        "emoji": source["emoji"]
                    })

    except Exception as e:
        print("Scrape error " + source["name"] + ": " + str(e))

    # ডুপ্লিকেট বাদ
    seen = set()
    unique_jobs = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique_jobs.append(job)

    return unique_jobs[:10]

# =============================================
# Telegram এ পাঠানো
# =============================================
def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

# =============================================
# মেইন ফাংশন
# =============================================
def check_new_jobs():
    global sent_jobs
    print("Checking for new government jobs... " + datetime.now().strftime("%H:%M:%S"))
    new_count = 0

    for source in JOB_SOURCES:
        jobs = scrape_jobs(source)

        for job in jobs:
            if job["id"] in sent_jobs:
                continue

            # AI দিয়ে বিশ্লেষণ
            analysis = analyze_job(job["title"], "")

            message = (
                job["emoji"] + " <b>নতুন সরকারি চাকরির বিজ্ঞপ্তি!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🏢 <b>সূত্র:</b> " + job["source"] + "\n\n"
                "📄 <b>" + job["title"][:200] + "</b>\n\n"
                + analysis + "\n\n"
                "🔗 <a href='" + job["url"] + "'>বিস্তারিত দেখুন</a>"
            )

            if send_telegram(message):
                sent_jobs.add(job["id"])
                new_count += 1
                print("Job sent: " + job["title"][:50])
                time.sleep(3)

    save_sent_jobs(sent_jobs)

    if new_count > 0:
        print(str(new_count) + " new jobs sent!")
    else:
        print("No new jobs found.")

# =============================================
# মেইন প্রোগ্রাম
# =============================================
if __name__ == "__main__":
    print("Government Job Alert Bot starting...")

    # প্রথমবার সব পুরনো জব লোড করো
    print("Loading existing jobs to avoid duplicates...")
    for source in JOB_SOURCES:
        jobs = scrape_jobs(source)
        for job in jobs:
            sent_jobs.add(job["id"])
    save_sent_jobs(sent_jobs)
    print("Loaded " + str(len(sent_jobs)) + " existing jobs. Now watching for NEW jobs...")

    # প্রতি ৩০ মিনিটে চেক করবে
    schedule.every(30).minutes.do(check_new_jobs)

    print("Bot running... Checking every 30 minutes for new government jobs.")
    while True:
        schedule.run_pending()
        time.sleep(60)
