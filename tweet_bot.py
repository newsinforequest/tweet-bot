import os
import feedparser
import tweepy
import random
import requests
import tempfile
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from transformers import pipeline

# 🔐 API keys
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# 🌍 RSS-feeds per werelddeel
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

summarizer = pipeline("summarization")
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-en")

def authenticate():
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)

def fetch_articles():
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    seen_titles = {}

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
                        title = entry.title.strip()
                        if title not in seen_titles:
                            seen_titles[title] = entry
            except Exception as e:
                print(f"⚠️ Fout bij {url}: {e}")

    return seen_titles

def generate_clickbait(title):
    words = title.split()
    return ' '.join(words[:5]).upper()

def summarize_and_translate(text):
    try:
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
        translation = translator(summary)[0]['translation_text']
        return translation
    except Exception as e:
        print(f"⚠️ Samenvatting/vertaalfout: {e}")
        return None

def extract_image_url(entry):
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get('url')
    elif "summary" in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    return None

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

def tweet_article(api, title, summary, image_url=None):
    headline = generate_clickbait(title)
    body = summarize_and_translate(summary)
    if not body:
        return

    tweet = f"{headline} 🚨\n\n{body}"
    # Garandeer lengte tussen 265-280 tekens
    if len(tweet) < 265:
        tweet += " " + ("🔥" * ((265 - len(tweet)) // 2))
    tweet = tweet[:280]

    media_id = None
    if image_url:
        image_path = download_image(image_url)
        if image_path:
            try:
                media = api.media_upload(image_path)
                media_id = media.media_id
            except Exception as e:
                print(f"⚠️ Upload afbeelding mislukt: {e}")

    try:
        if media_id:
            api.update_status(status=tweet, media_ids=[media_id])
        else:
            api.update_status(status=tweet)
        print("✅ Tweet geplaatst.")
    except Exception as e:
        print(f"⚠️ Tweet fout: {e}")

def main():
    api = authenticate()
    articles = fetch_articles()
    if not articles:
        print("❌ Geen recente artikelen gevonden.")
        return
    title, entry = random.choice(list(articles.items()))
    summary = entry.summary if 'summary' in entry else ""
    image_url = extract_image_url(entry)
    tweet_article(api, title, summary, image_url)

if __name__ == "__main__":
    main()
