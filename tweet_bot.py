import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import requests
from bs4 import BeautifulSoup
import nltk
from collections import Counter
import re
import time

nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords
# from nltk.tokenize import word_tokenize

EN_STOPWORDS = set(stopwords.words('english'))

# Twitter API v2 authenticatie via Tweepy Client
def authenticate_v2():
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    return client

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

def fetch_recent_articles():
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    articles = []

    for feeds in RSS_FEEDS.values():
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6])
                    except (AttributeError, TypeError):
                        continue
                    if pub_time >= one_hour_ago:
                        articles.append({
                            "title": entry.title.strip(),
                            "link": entry.link.strip(),
                            "published": pub_time
                        })
            except Exception as e:
                print(f"⚠️ Fout bij feed {url}: {e}")

    return articles

def extract_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Probeer hoofdtekst te vinden op basis van tag/density
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        print(f"⚠️ Kan artikel niet openen: {url} - {e}")
        return ""

def detect_common_topic(articles):
    all_words = []
    article_bodies = {}

    for article in articles:
        content = extract_article_text(article["link"])
        article_bodies[article["title"]] = content

        tokens = re.findall(r'\b\w+\b', content.lower())
        words = [w for w in tokens if w.isalpha() and w not in EN_STOPWORDS]
        all_words.extend(words)

    common_words = Counter(all_words).most_common(10)
    if not common_words:
        return None, article_bodies

    top_keyword = common_words[0][0]
    matching_article = next((t for t, body in article_bodies.items() if top_keyword in body.lower()), None)
    return matching_article, article_bodies

def summarize_text(text, length=270):
    sentences = nltk.sent_tokenize(text)
    summary = ''
    for s in sentences:
        if len(summary) + len(s) <= length:
            summary += ' ' + s
        else:
            break
    return summary.strip()[:280]

def generate_clickbait(title):
    words = title.split()
    return ' '.join(words[:5]) if len(words) > 5 else title

def tweet_article(client, title, summary):
    clickbait = generate_clickbait(title)
    tweet = f"{clickbait}\n\n{summary}"
    tweet = tweet.replace('\n', ' ').replace('\r', ' ').strip()
    if len(tweet) > 280:
        tweet = tweet[:279]
    try:
        response = client.create_tweet(text=tweet)
        print(f"✅ Tweet geplaatst: {tweet} (ID: {response.data['id']})")
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

def main():
    client = authenticate_v2()
    articles = fetch_recent_articles()
    if not articles:
        print("❌ Geen artikelen gevonden.")
        return

    best_title, bodies = detect_common_topic(articles)
    if best_title and best_title in bodies:
        summary = summarize_text(bodies[best_title])
        tweet_article(client, best_title, summary)
    else:
        print("❌ Geen geschikt artikel gevonden.")

if __name__ == "__main__":
    main()
