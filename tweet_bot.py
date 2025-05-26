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
        "https://www.nzherald.co.nz/rss/"
    ]
}

def authenticate_v2():
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    return client

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
    three_hours_ago = now - timedelta(hours=3)
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
                    if pub_time >= three_hours_ago:
                        articles.append({
                            "title": entry.title.strip(),
                            "link": entry.link.strip(),
                            "published": pub_time
                        })
            except:
                pass

    return articles

def extract_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')

        paragraphs = soup.find_all('p')
        cleaned_paragraphs = []
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) < 40:
                continue
            if re.search(r'(?i)(privacy|newsletter|search|contact|language|subscribe|cookie)', text):
                continue
            cleaned_paragraphs.append(text)

        text = ' '.join(cleaned_paragraphs)
        text = re.sub(r'\s+', ' ', text).strip()

        if detect_language(text) != "en":
            text = translate_to_english(text)

        return text
    except:
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

def rewrite_text(text, min_length=240, max_length=280):
    sentences = re.split(r'(?<=[.!?]) +', text)
    best_candidate = ''
    for start in range(len(sentences)):
        rewritten = ''
        for end in range(start + 1, len(sentences) + 1):
            trial = ' '.join(sentences[start:end]).strip()
            if len(trial) > max_length:
                break
            rewritten = trial
        if min_length <= len(rewritten) <= max_length:
            return rewritten
        if len(rewritten) > len(best_candidate):
            best_candidate = rewritten
    return best_candidate if len(best_candidate) >= min_length else ''

def generate_clickbait(text):
    summary = rewrite_text(text, 20, 60)
    return summary.upper()

def clean_summary_text(text):
    text = re.sub(r'\(Photo:.*?\)', '', text)
    text = re.sub(r'(?i)^(search the news|personalise the news|emergency backstory|newsletters|[a-z\s]{0,20}(中文|BERITA|TOK PISIN|ABC|TOPIC).{0,20})[:\s-]*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tweet_article(client, summary_text):
    if detect_language(summary_text) != "en":
        return
    summary_text = clean_summary_text(summary_text)
    clickbait = generate_clickbait(summary_text)
    tweet = f"{clickbait}\n\n{summary_text}"
    tweet = tweet.replace('\n', ' ').replace('\r', ' ').strip()
    try:
        client.create_tweet(text=tweet)
    except tweepy.TooManyRequests:
        print("⛔ Te veel verzoeken (429), script stopt tot volgende cyclus.")
        exit(0)
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

def main():
    client = authenticate_v2()
    articles = fetch_recent_articles()
    if not articles:
        return

    while articles:
        best_title, bodies = detect_common_topic(articles)
        if best_title and best_title in bodies:
            rewritten = rewrite_text(bodies[best_title])
            if 240 <= len(rewritten) <= 280:
                if detect_language(rewritten) != "en":
                    rewritten = translate_to_english(rewritten)
                tweet_article(client, rewritten)
                return
            else:
                articles = [a for a in articles if a["title"] != best_title]
        else:
            break

if __name__ == "__main__":
    main()
