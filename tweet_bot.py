import feedparser
import random
import time
from datetime import datetime, timedelta
import tweepy
import os

# Twitter API keys (vervang met je eigen keys of stel in als secrets/environment vars)
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Werelddeel RSS-feeds
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

def fetch_articles():
    print("✅ Nieuwsartikel ophalen...")
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    seen_titles = {}
    
    for continent, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6])
                    except (AttributeError, TypeError):
                        continue

                    if pub_time >= one_hour_ago:
                        title = entry.title.strip()
                        if title not in seen_titles:
                            seen_titles[title] = set()
                        seen_titles[title].add(continent)
            except Exception as e:
                print(f"⚠️ Fout bij verwerken van feed: {feed_url} - {e}")
    
    return seen_titles

def generate_clickbait(title):
    words = title.split()
    if len(words) <= 5:
        return title
    return ' '.join(words[:5])

def select_article(articles, last_tweet=""):
    candidates = [title for title, continents in articles.items() if len(continents) >= 2]
    if candidates:
        selected = random.choice(candidates)
    elif articles:
        # Kies de meest besproken of willekeurig
        sorted_articles = sorted(articles.items(), key=lambda item: len(item[1]), reverse=True)
        top_titles = [t for t, v in sorted_articles if len(v) == len(sorted_articles[0][1])]
        if last_tweet:
            top_titles = sorted(top_titles, key=lambda t: overlap(t, last_tweet))
        selected = top_titles[0]
    else:
        return None
    return selected

def overlap(a, b):
    return len(set(a.lower().split()) & set(b.lower().split()))

def tweet_article(api, text):
    tweet = generate_clickbait(text)
    tweet = tweet.replace('\n', ' ').replace('\r', '')
    try:
        api.update_status(tweet)
        print(f"✅ Tweet geplaatst: {tweet}")
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

def authenticate():
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)

def main():
    api = authenticate()
    last_tweet = ""
    articles = fetch_articles()
    if not articles:
        print("❌ Geen recente artikelen gevonden.")
        return
    selected_title = select_article(articles, last_tweet)
    if selected_title:
        tweet_article(api, selected_title)
        last_tweet = selected_title
    else:
        print("❌ Geen geschikte tweet gevonden.")

if __name__ == "__main__":
    main()
