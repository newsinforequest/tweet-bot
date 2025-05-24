import feedparser
import openai
import tweepy
import os
import datetime
import random
from time import sleep
from collections import Counter

# ✅ API-sleutels uit environment
openai.api_key = os.getenv("OPENAI_API_KEY")

client = tweepy.Client(
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
        "https://www.lanacion.com.ar/rss-secciones-politica/"
    ]
}

# 🆘 Fallback-feeds (voorbeeld: vul aan tot 100)
FALLBACK_FEEDS = [
    "https://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.foxnews.com/foxnews/latest",
    "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
    "https://www.washingtonpost.com/rss/",
    "https://www.nbcnews.com/id/3032091/device/rss/rss.xml",
    "https://www.cbsnews.com/latest/rss/main",
    "https://abcnews.go.com/abcnews/topstories",
    "https://www.reuters.com/tools/rss",
    "https://www.economist.com/the-world-this-week/rss.xml",
    "https://www.dw.com/en/top-stories/s-9097/rss",
    "https://www.apnews.com/rss",
    "https://www.bloomberg.com/feed/podcast/taking-stock.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://globalvoices.org/-/world/feed/",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/uk/rss",
    "https://www.telegraph.co.uk/news/rss.xml",
    "https://rss.itv.com/news",
    "https://www.independent.co.uk/news/uk/rss",
    "https://globalnews.ca/feed/",
    "https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009",
    "https://www.cbc.ca/cmlink/rss-topstories",
    "https://www.smh.com.au/rss/feed.xml",
    "https://www.abc.net.au/news/feed/51120/rss.xml",
    "https://www.news.com.au/feed",

# 🧠 Thema fallback-feeds (evergreen topics)
THEME_FEEDS = {
    "Climate": ["https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "AI": ["https://spectrum.ieee.org/rss/artificial-intelligence/fulltext"],
    "Geopolitics": ["https://foreignpolicy.com/feed/"]
}

# 📅 Filter: maximaal 1 uur oud
def is_recent(entry):
    if not hasattr(entry, 'published_parsed'):
        return False
    pub_date = datetime.datetime(*entry.published_parsed[:6])
    return (datetime.datetime.utcnow() - pub_date) <= datetime.timedelta(hours=1)

# 🤖 Samenvatten tussen 260–280 tekens
def summarize_to_exact_length(text, min_len=260, max_len=280, max_attempts=5):
    for attempt in range(max_attempts):
        prompt = (
            f"Summarize the following news text in English in exactly one paragraph. "
            f"Make it concise but informative, and aim for a length between {min_len} and {max_len} characters:\n\n"
            f"{text}\n\nSummary:"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_len + 20
        )
        summary = response.choices[0].message["content"].strip()
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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=10
    )
    return response.choices[0].message["content"].strip()

# 📰 Artikelen verzamelen per feed
def gather_articles(feeds):
    articles = []
    for continent, urls in feeds.items():
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if is_recent(entry):
                    summary = entry.summary if hasattr(entry, 'summary') else entry.title
                    if len(summary) >= 400:
                        articles.append({
                            "continent": continent,
                            "title": entry.title,
                            "summary": summary,
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

    # Voorkeur 1: onderwerp op meerdere continenten
    preferred = [title for title, continents in continent_map.items() if len(continents) >= 2]

    # Voorkeur 2: onderwerp meerdere keren in uur
    preferred = sorted(preferred, key=lambda t: freq_counter[t], reverse=True)

    if preferred:
        return title_map[preferred[0]][0]  # eerste artikel van voorkeursitem
    return None

# 🐦 Tweet maken en posten
def tweet_article(article):
    clickbait = generate_clickbait(article["title"])
    summary = summarize_to_exact_length(article["summary"])
    tweet = f"{clickbait}: {summary} {article['link']}"

    if len(tweet) > 280:
        # Optioneel: clickbait afkappen als het geheel te lang is
        excess = len(tweet) - 280
        clickbait = clickbait[:-excess - 1]  # -1 voor de dubbele punt
        tweet = f"{clickbait}: {summary} {article['link']}"

    try:
        response = client.create_tweet(text=tweet)
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
        fallback_feed_map = {f"Fallback{i}": [url] for i, url in enumerate(FALLBACK_FEEDS)}
        fallback_articles = gather_articles(fallback_feed_map)

        fallback_counter = Counter([a["title"] for a in fallback_articles])
        if fallback_counter:
            top_fallback_title = fallback_counter.most_common(1)[0][0]
            article = next(a for a in fallback_articles if a["title"] == top_fallback_title)

    if not article:
        print("⚠️ Nog steeds geen artikel gevonden, gebruik thema fallback.")
        theme_articles = gather_articles(THEME_FEEDS)
        if theme_articles:
            article = random.choice(theme_articles)

    if article:
        tweet_article(article)
    else:
        print("🚫 Geen geschikt artikel gevonden, zelfs niet in thema-feeds.")

if __name__ == "__main__":
    run_bot()
