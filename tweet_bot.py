import feedparser
import tweepy
import os
import datetime
import random
from time import sleep
from collections import Counter
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

# ✅ API-sleutels uit environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

client_twitter = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

# 🌍 RSS-feeds per continent
FEEDS = {
    "Europa": [
        "https://www.nrc.nl/rss/",
        "https://www.bbc.co.uk/news/world/europe/rss.xml",
        "https://www.spiegel.de/international/index.rss",
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.rt.com/rss/news"
    ],
    "Azië": [
        "https://english.kyodonews.net/rss/news.xml",
        "https://www.japantimes.co.jp/feed/",
        "https://www.channelnewsasia.com/rssfeeds/8395986",
        "https://www.scmp.com/rss/91/feed",
        "https://www.koreatimes.co.kr/www/rss/rss.xml"
    ],
    "Afrika": [
        "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "https://www.news24.com/news24/rss",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.ghanaweb.com/GhanaHomePage/NewsArchive/rss.xml",
        "https://www.sabcnews.com/sabcnews/category/africa/feed/"
    ],
    "Noord-Amerika": [
        "https://rss.cnn.com/rss/cnn_topstories.rss",
        "https://feeds.npr.org/1001/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.foxnews.com/foxnews/latest",
        "https://globalnews.ca/feed/"
    ],
    "Zuid-Amerika": [
        "https://www1.folha.uol.com.br/folhaemrss.xml",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america",
        "https://www.telesurenglish.net/rss/",
        "https://www.infobae.com/america/rss.xml",
        "https://www.lanacion.com.ar/rss-secties-politica/"
    ]
}

# 🆘 Fallback-feeds (gevalideerd)
FALLBACK_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://cnbc.com/id/100727362/device/rss/rss.html",
    "https://abcnews.go.com/abcnews/internationalheadlines",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.cbsnews.com/latest/rss/world",
    "https://www.france24.com/en/rss",
    "https://www.buzzfeed.com/world.xml",
    "https://www.nytimes.com/svc/collections/v1/publishers/nyt/world/index.xml",
    "https://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.foxnews.com/foxnews/latest",
    "https://www.dw.com/en/top-stories/s-9097/rss",
    "https://globalnews.ca/feed/",
    "https://www.cbc.ca/webfeed/rss/rss-world"
]

# 🧠 Thema fallback-feeds (evergreen topics)
THEME_FEEDS = {
    "Climate": ["https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "AI": ["https://spectrum.ieee.org/rss/artificial-intelligence/fulltext"],
    "Geopolitics": ["https://foreignpolicy.com/feed/"]
}

# 📅 Filter: maximaal 6 uur oud (voor debugging)
def is_recent(entry):
    if not hasattr(entry, 'published_parsed'):
        return False
    pub_date = datetime.datetime(*entry.published_parsed[:6])
    return (datetime.datetime.utcnow() - pub_date) <= datetime.timedelta(hours=6)

# 🧪 Artikelinhoud ophalen via URL

def extract_main_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)
        return text.strip()[:4000]  # Maximaal 4000 tekens ter beveiliging
    except Exception as e:
        print(f"⚠️ Fout bij ophalen inhoud van {url}: {e}")
        return ""

# 🤖 Samenvatten tussen 260–280 tekens

def summarize_to_exact_length(text, min_len=260, max_len=280, max_attempts=5):
    for attempt in range(max_attempts):
        prompt = (
            f"Summarize the following news text in English in exactly one paragraph. "
            f"If the original summary is too short, intelligently add relevant context or implications to meet the length requirement.\n\n"
            f"Text:\n{text}\n\nSummary:"
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_len + 20
        )
        summary = response.choices[0].message.content.strip()
        length = len(summary)

        if min_len <= length <= max_len:
            print(f"✅ Samenvatting gelukt ({length} tekens)")
            return summary
        else:
            print(f"⏳ Poging {attempt + 1}: Samenvatting is {length} tekens lang, opnieuw proberen...")
            sleep(1)

    print("⚠️ Samenvatting niet binnen limiet, laatste versie gebruiken.")
    return summary

# 🎯 Clickbait-titel van 1–5 woorden
def generate_clickbait(title):
    prompt = f"Write a short, clickbait-style headline (1–5 words) based on the following news title:\n\n{title}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=10
    )
    return response.choices[0].message.content.strip()

# 📰 Artikelen verzamelen per feed
def gather_articles(feeds):
    articles = []
    for continent, urls in feeds.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                print(f"⚠️ Fout bij feed {url}: {e}")
                continue
            for entry in feed.entries:
                if not is_recent(entry):
                    continue
                articles.append({
                    "continent": continent,
                    "title": entry.title,
                    "link": entry.link
                })
    return articles

# 🌐 Voorkeur 1 en 2 selectie

def select_preferred_article(articles):
    title_map = {}
    continent_map = {}
    freq_counter = Counter()

    for article in articles:
        title = article["title"]
        freq_counter[title] += 1
        title_map.setdefault(title, []).append(article)
        continent_map.setdefault(title, set()).add(article["continent"])

    all_titles = sorted(freq_counter.keys(), key=lambda t: (freq_counter[t], len(continent_map[t])), reverse=True)

    if all_titles:
        return title_map[all_titles[0]][0]
    return None

# 🐦 Tweet maken en posten
def tweet_article(article):
    clickbait = generate_clickbait(article["title"])
    full_text = extract_main_text(article["link"])
    if not full_text:
        print("⚠️ Geen inhoud gevonden, gebruik title als samenvatting")
        full_text = article["title"]
    summary = summarize_to_exact_length(full_text)
    tweet = f"{clickbait}: {summary} {article['link']}"

    print(f"📏 Tweetlengte: {len(tweet)}")
    print(f"🧪 Tweet preview: {repr(tweet)}")

    if len(tweet) > 280:
        excess = len(tweet) - 280
        clickbait = clickbait[:-excess - 1]  # -1 voor de dubbele punt
        tweet = f"{clickbait}: {summary} {article['link']}"

    try:
        response = client_twitter.create_tweet(text=tweet)
        print(f"✅ Tweet geplaatst: {tweet}")
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

# 🤖 Hoofdfunctie
def run_bot():
    print("🔎 Nieuws ophalen...")
    articles = gather_articles(FEEDS)

    article = select_preferred_article(articles)

    if not article:
        print("⚠️ Geen geschikt onderwerp gevonden, gebruik fallback feeds.")
        fallback_feed_map = {"Fallback": FALLBACK_FEEDS}
        fallback_articles = gather_articles(fallback_feed_map)
        article = select_preferred_article(fallback_articles)

    if not article:
        print("⚠️ Nog steeds geen artikel gevonden, gebruik thema fallback.")
        theme_articles = gather_articles(THEME_FEEDS)
        article = select_preferred_article(theme_articles)

    if article:
        tweet_article(article)
    else:
        print("🚫 Geen geschikt artikel gevonden, zelfs niet in thema-feeds.")

if __name__ == "__main__":
    run_bot()
