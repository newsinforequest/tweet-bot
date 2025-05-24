import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import requests
from bs4 import BeautifulSoup
import tempfile

# ✅ Twitter authenticatie
def authenticate_v2():
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    return client

# ✅ 5 RSS-feeds per continent
RSS_FEEDS = {
    "Europa": [
        "https://www.nrc.nl/rss/",
        "https://www.bbc.co.uk/news/world/europe/rss.xml",
        "https://www.spiegel.de/international/index.rss",
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.rt.com/rss/news"
    ],
    "Azië": [
        "https://timesofindia.indiatimes.com/rss.cms",
        "https://english.kyodonews.net/rss/news.xml",
        "https://www.japantimes.co.jp/feed/",
        "https://www.channelnewsasia.com/rssfeeds/8395986",
        "https://www.scmp.com/rss/91/feed"
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

# ✅ Artikelen ophalen en per continent mappen
def fetch_articles():
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    articles = {}

    for continent, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6])
                        if pub_time < one_hour_ago:
                            continue
                    except:
                        continue

                    title = entry.title.strip()
                    key = title.lower().strip()

                    if key not in articles:
                        articles[key] = {
                            "title": title,
                            "summary": entry.get("summary", ""),
                            "published": pub_time,
                            "continents": set(),
                            "sources": set(),
                            "entry": entry
                        }

                    articles[key]["continents"].add(continent)
                    articles[key]["sources"].add(url)

            except Exception as e:
                print(f"⚠️ Fout bij {url}: {e}")

    return list(articles.values())

# ✅ Afbeeldings-URL extraheren
def extract_image_url(entry):
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get("url")
    if "summary" in entry:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None

# ✅ Download afbeelding lokaal
def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp.write(response.content)
            temp.close()
            return temp.name
    except Exception as e:
        print(f"⚠️ Download afbeelding mislukt: {e}")
    return None

# ✅ Tweet genereren (met clickbait headline)
def generate_tweet(title, summary):
    headline = ' '.join(title.split()[:5]).upper()
    body = summary.strip().replace('\n', ' ')
    tweet = f"{headline} 🚨\n\n{body}"
    tweet = tweet.strip()

    if len(tweet) > 280:
        tweet = tweet[:279] + "…"
    elif len(tweet) < 270:
        tweet += " #BreakingNews"
    return tweet

# ✅ Artikel selecteren op basis van voorkeuren
def select_best_article(articles):
    if not articles:
        return None

    # Prioriteit 1: in meerdere continenten
    multi_continent = [a for a in articles if len(a["continents"]) >= 2]
    if multi_continent:
        return random.choice(multi_continent)

    # Prioriteit 2: meerdere bronnen
    multi_source = [a for a in articles if len(a["sources"]) >= 2]
    if multi_source:
        return random.choice(multi_source)

    # Prioriteit 3: meest recente
    return sorted(articles, key=lambda a: a["published"], reverse=True)[0]

# ✅ Tweet plaatsen (met optionele afbeelding)
def tweet_article(client, article):
    tweet = generate_tweet(article["title"], article["summary"])
    image_url = extract_image_url(article["entry"])
    media_id = None

    if image_url:
        image_path = download_image(image_url)
        if image_path:
            try:
                media = client.media_upload(filename=image_path)
                media_id = media.media_id
            except Exception as e:
                print(f"⚠️ Afbeelding upload fout: {e}")

    try:
        if media_id:
            response = client.create_tweet(text=tweet, media_ids=[media_id])
        else:
            response = client.create_tweet(text=tweet)
        print(f"✅ Tweet geplaatst (ID: {response.data['id']})")
    except Exception as e:
        print(f"⚠️ Tweet fout: {e}")

# ✅ Main
def main():
    client = authenticate_v2()
    articles = fetch_articles()
    article = select_best_article(articles)
    if article:
        tweet_article(client, article)
    else:
        print("❌ Geen geschikt artikel gevonden.")

if __name__ == "__main__":
    main()
