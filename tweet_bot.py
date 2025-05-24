import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import requests
from bs4 import BeautifulSoup

# Twitter API authenticatie v2 (voor tweets)
def authenticate_v2():
    return tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )

# Twitter API authenticatie v1.1 (voor media upload)
def authenticate_v1():
    auth = tweepy.OAuth1UserHandler(
        os.getenv("TWITTER_API_KEY"),
        os.getenv("TWITTER_API_SECRET"),
        os.getenv("TWITTER_ACCESS_TOKEN"),
        os.getenv("TWITTER_ACCESS_SECRET")
    )
    return tweepy.API(auth)

# RSS-feeds per continent (5 per continent)
RSS_FEEDS = {
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

# Fallback wereldwijde feeds (voorbeeld)
FALLBACK_FEEDS = [
    "https://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.foxnews.com/foxnews/latest",
    # etc. ...
]

# HTML opschonen
def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

# Artikelen ophalen en filteren
def fetch_articles():
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=1)
    articles = {}

    for region, feeds in RSS_FEEDS.items():
        for feed in feeds:
            try:
                parsed = feedparser.parse(feed)
                for entry in parsed.entries:
                    try:
                        pub = datetime(*entry.published_parsed[:6])
                    except:
                        continue
                    if pub < cutoff:
                        continue
                    title = entry.title.strip()
                    link = entry.link
                    summary = clean_html(entry.summary if 'summary' in entry else "")
                    if len(summary) >= 400:
                        if title not in articles:
                            articles[title] = {"summary": summary, "link": link, "regions": set(), "image": None}
                        articles[title]["regions"].add(region)
                        if 'media_content' in entry:
                            articles[title]["image"] = entry.media_content[0].get('url', None)
            except Exception:
                continue
    return articles

# Alternatief: fallback artikel zoeken
def fetch_fallback_article():
    for feed_url in FALLBACK_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                pub = datetime(*entry.published_parsed[:6])
                if datetime.utcnow() - pub > timedelta(hours=1):
                    continue
                title = entry.title.strip()
                summary = clean_html(entry.summary if 'summary' in entry else "")
                if len(summary) >= 400:
                    return {
                        "title": title,
                        "summary": summary,
                        "link": entry.link,
                        "image": entry.media_content[0].get('url') if 'media_content' in entry else None
                    }
        except:
            continue
    return None

# Selecteer artikel met voorkeuren
def select_article(articles):
    high_priority = [a for a in articles.items() if len(a[1]["regions"]) >= 2]
    multi_source = [a for a in articles.items() if len(a[1]["regions"]) == 1]
    if high_priority:
        return random.choice(high_priority)
    elif multi_source:
        return random.choice(multi_source)
    elif articles:
        return sorted(articles.items(), key=lambda x: len(x[1]["summary"]), reverse=True)[0]
    else:
        return None

# Clickbait titel (1–5 woorden)
def generate_title(text):
    words = text.strip().split()
    return " ".join(words[:random.randint(1, min(5, len(words)))])

# Samenvatting → tweet (270-280 tekens)
def summarize_to_tweet(summary, max_len=280, min_len=270):
    text = clean_html(summary).replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    elif len(text) < min_len:
        return text + ("." * (min_len - len(text)))
    return text

# Afbeelding downloaden en uploaden via v1.1 API
def upload_image(api_v1, image_url):
    try:
        filename = "temp.jpg"
        with open(filename, 'wb') as f:
            f.write(requests.get(image_url).content)
        media = api_v1.media_upload(filename)
        os.remove(filename)
        return media.media_id
    except Exception as e:
        print(f"Afbeelding upload mislukt: {e}")
        return None

# Tweet publiceren met v2 client en media via v1 API
def tweet_article(client_v2, client_v1, title, summary, image_url=None):
    tweet_title = generate_title(title).upper()
    tweet_body = summarize_to_tweet(summary)
    full_text = f"{tweet_title}\n\n{tweet_body}"
    try:
        if image_url:
            media_id = upload_image(client_v1, image_url)
            if media_id:
                response = client_v2.create_tweet(text=full_text, media_ids=[media_id])
            else:
                response = client_v2.create_tweet(text=full_text)
        else:
            response = client_v2.create_tweet(text=full_text)
        print("✅ Tweet geplaatst:", response.data["id"])
    except Exception as e:
        print("❌ Fout bij tweet:", e)

# Main
def main():
    client_v2 = authenticate_v2()
    client_v1 = authenticate_v1()

    articles = fetch_articles()
    selection = select_article(articles)

    if selection:
        title, data = selection
        tweet_article(client_v2, client_v1, title, data["summary"], data["image"])
    else:
        fallback = fetch_fallback_article()
        if fallback:
            tweet_article(client_v2, client_v1, fallback["title"], fallback["summary"], fallback["image"])
        else:
            print("❌ Geen geschikt artikel gevonden.")

if __name__ == "__main__":
    main()
