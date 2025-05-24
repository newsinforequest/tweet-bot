import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import time
from langdetect import detect

from nltk.corpus import stopwords
from nltk import download

try:
    download('stopwords')
except:
    pass

EN_STOPWORDS = set(stopwords.words('english'))

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
        "https://www.bbc.co.uk/news/world/europe/rss.xml",
        "https://www.spiegel.de/international/index.rss",
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
        "https://www.telesurenglish.net/rss/"
    ],
    "Oceanië": [
        "https://www.abc.net.au/news/feed/51120/rss.xml",
        "https://www.nzherald.co.nz/rss/"
    ],
    "Fallback": [
        "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
        "https://www.dw.com/en/top-stories/s-9097?maca=en-rss-en-all-1573-rdf",
        "https://www.abc.net.au/news/feed/51120/rss.xml",
        "https://www.al-monitor.com/rss.xml",
        "https://apnews.com/rss",
        "https://rss.dw.com/rdf/rss-en-all",
        "https://www.nationalgeographic.com/content/natgeo/en_us/index.rss",
        "https://www.voanews.com/api/epiqqe$omm",
        "https://www.hindustantimes.com/rss/topnews/rssfeed.xml",
        "https://www.cbc.ca/cmlink/rss-topstories",
        "https://www.nzherald.co.nz/rss/"
    ]
}

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def translate_to_english(text):
    try:
        response = requests.post(
            "https://libretranslate.de/translate",
            data={
                "q": text,
                "source": "auto",
                "target": "en",
                "format": "text"
            }
        )
        return response.json()["translatedText"]
    except:
        return text

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

        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        text = re.sub(r'\s+', ' ', text).strip()

        if detect_language(text) != "en":
            text = translate_to_english(text)

        return text
    except Exception as e:
        print(f"⚠️ Kan artikel niet openen of vertalen: {url} - {e}")
        return ""

def detect_common_topic(articles):
    article_bodies = {}

    for article in articles:
        content = extract_article_text(article["link"])
        if detect_language(content) != "en" or len(content.split()) < 75:
            continue
        article_bodies[article["title"]] = content

    if not article_bodies:
        return None, {}

    best_title = max(article_bodies.items(), key=lambda x: len(x[1].split()))[0]
    return best_title, article_bodies

def summarize_text(text, min_length=240, max_length=280):
    sentences = re.split(r'(?<=[.!?]) +', text)
    for start in range(len(sentences)):
        summary = ''
        for end in range(start + 1, len(sentences) + 1):
            trial = ' '.join(sentences[start:end]).strip()
            if len(trial) > max_length:
                break
            summary = trial
        if min_length <= len(summary) <= max_length:
            return summary
    return ''

def generate_clickbait(title):
    words = title.split()
    return ' '.join(words[:5]) if len(words) > 5 else title

def tweet_article(client, title, summary):
    if detect_language(summary) != "en":
        print("⚠️ Samenvatting is niet in het Engels, tweet wordt overgeslagen.")
        return
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

    while articles:
        best_title, bodies = detect_common_topic(articles)
        if best_title and best_title in bodies:
            summary = summarize_text(bodies[best_title])
            if 240 <= len(summary) <= 280:
                if detect_language(summary) != "en":
                    summary = translate_to_english(summary)
                tweet_article(client, best_title, summary)
                return
            else:
                articles = [a for a in articles if a["title"] != best_title]
        else:
            break

    print("❌ Geen geschikt artikel gevonden met voldoende lengte.")

if __name__ == "__main__":
    main()
