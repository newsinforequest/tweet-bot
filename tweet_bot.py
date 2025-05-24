import feedparser
import time
import random
import tweepy
from datetime import datetime, timedelta

# =========================
# Twitter API authenticatie
# =========================
CONSUMER_KEY = 'YOUR_CONSUMER_KEY'
CONSUMER_SECRET = 'YOUR_CONSUMER_SECRET'
ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'
ACCESS_TOKEN_SECRET = 'YOUR_ACCESS_TOKEN_SECRET'

auth = tweepy.OAuth1UserHandler(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# ====================
# RSS-feeds per regio
# ====================
rss_feeds = {
    'europe': [
        "http://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://www.thelocal.de/feeds/rss.php",
        "https://www.euractiv.com/section/politics/feed/",
        "https://www.politico.eu/feed/",
        "https://www.rt.com/rss/news/"
    ],
    'asia': [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://japantoday.com/category/national/rss",
        "https://www.koreatimes.co.kr/www/rss/nation.xml",
        "https://www.straitstimes.com/news/asia/rss.xml"
    ],
    'africa': [
        "https://www.aljazeera.com/xml/rss/all.xml?region=africa",
        "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "https://ewn.co.za/RSSFeed",
        "https://www.bbc.co.uk/news/world/africa/rss.xml",
        "https://mg.co.za/feed/"
    ],
    'north_america': [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "http://feeds.foxnews.com/foxnews/latest",
        "https://www.cbc.ca/cmlink/rss-world",
        "https://www.npr.org/rss/rss.php?id=1001",
        "https://rss.cnn.com/rss/edition_world.rss"
    ],
    'south_america': [
        "https://www.batimes.com.ar/rss/feed.xml",
        "https://www.brazilian.report/feed/",
        "https://rioonwatch.org/?feed=rss2",
        "https://www.americasquarterly.org/feed/",
        "https://english.elpais.com/rss/"
    ]
}

# ================
# Artikelen ophalen
# ================
def fetch_articles():
    articles = []
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    for region, feeds in rss_feeds.items():
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = datetime(*entry.published_parsed[:6])
                    if pub_time > one_hour_ago:
                        articles.append({
                            'title': entry.title,
                            'summary': entry.get('summary', ''),
                            'region': region,
                            'time': pub_time
                        })
    return articles

# ===========================
# Trending onderwerp bepalen
# ===========================
def select_trending_topic(articles, previous_topic=None):
    from collections import Counter
    topic_counter = Counter([a['title'] for a in articles])
    common_topics = topic_counter.most_common()

    if not common_topics:
        return random.choice(articles)

    for topic, count in common_topics:
        if count >= 2:
            candidates = [a for a in articles if a['title'] == topic]
            return random.choice(candidates)

    # fallback naar trending artikel
    fallback = common_topics[0][0]
    return random.choice([a for a in articles if a['title'] == fallback])

# ====================
# Tweet opstellen
# ====================
def generate_tweet(article):
    title = article['title'].strip().split(' - ')[0]
    title_words = title.split()
    clickbait_title = ' '.join(title_words[:5])

    summary = article['summary']
    tweet = f"{clickbait_title} — {summary}"
    tweet = tweet.replace('\n', ' ').replace('\r',
