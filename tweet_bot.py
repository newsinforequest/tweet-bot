import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import requests
from bs4 import BeautifulSoup
import html
import re

def authenticate_v2():
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    return client

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
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    articles = {}

    for continent, feeds in RSS_FEEDS.items():
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                try:
                    pub_time = datetime(*entry.published_parsed[:6])
                except (AttributeError, TypeError):
                    continue
                if pub_time < one_hour_ago:
                    continue

                title = html.unescape(entry.title.strip())
                content = html.unescape(get_article_text(entry))
                if len(content) < 400:
                    continue

                key = (title, content)
                if key not in articles:
                    articles[key] = {"continents": set(), "published": pub_time, "image": extract_image_url(entry)}
                articles[key]["continents"].add(continent)

    return articles

def get_article_text(entry):
    if hasattr(entry, 'summary'):
        return re.sub(r'<[^>]+>', '', entry.summary)
    return ""

def extract_image_url(entry):
    if "media_content" in entry:
        return entry.media_content[0].get('url')
    elif hasattr(entry, 'summary'):
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    return None

def generate_clickbait(text):
    words = text.split()
    return ' '.join(words[:min(5, len(words))]).upper()

def compose_tweet(title, content):
    headline = generate_clickbait(title)
    rest = content.strip().replace('\n', ' ')
    tweet = f"{headline} 🚨 {rest}"
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    if len(tweet) < 270:
        return None
    return tweet

def select_best_article(articles):
    sorted_articles = sorted(articles.items(), key=lambda kv: (-len(kv[1]['continents']), -kv[1]['published'].timestamp()))
    return sorted_articles[0] if sorted_articles else (None, None)

def tweet_article(client, title, content, image_url=None):
    tweet = compose_tweet(title, content)
    if not tweet:
        print("⛔ Tweet te kort, overgeslagen.")
        return
    media_id = None
    if image_url:
        try:
            img_data = requests.get(image_url).content
            with open("temp.jpg", "wb") as f:
                f.write(img_data)
            media = client.media_upload(filename="temp.jpg")
            media_id = media.media_id
        except:
            pass
    try:
        client.create_tweet(text=tweet, media_ids=[media_id] if media_id else None)
        print("✅ Tweet geplaatst:", tweet)
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

def main():
    client = authenticate_v2()
    articles = fetch_articles()
    title_content, meta = select_best_article(articles)
    if not title_content:
        print("❌ Geen geschikt artikel gevonden.")
        return
    title, content = title_content
    tweet_article(client, title, content, meta["image"])

if __name__ == "__main__":
    main()
