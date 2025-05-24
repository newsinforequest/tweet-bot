
import os
import tweepy
import time
import feedparser
from datetime import datetime, timedelta

# Twitter API keys from environment
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# RSS feeds per continent (at least 5 per)
rss_feeds = {
    "europe": [
        "http://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://www.rtbf.be/info/rss/monde.xml",
        "https://www.derstandard.at/rss",
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.spiegel.de/international/index.rss"
    ],
    "asia": [
        "https://www.scmp.com/rss/91/feed",
        "https://www.japantimes.co.jp/feed/",
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.chinadaily.com.cn/rss/china_rss.xml"
    ],
    "africa": [
        "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "https://www.bbc.co.uk/news/world/africa/rss.xml",
        "https://ewn.co.za/RSS",
        "https://www.theeastafrican.co.ke/feeds/2543720-2543720-format-rss-6rjdh0z/index.xml",
        "https://www.voaafrica.com/api/zrripe_vqopi"
    ],
    "north_america": [
        "http://rss.cnn.com/rss/edition_us.rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.foxnews.com/foxnews/latest",
        "https://www.npr.org/rss/rss.php?id=1004",
        "https://www.cbc.ca/cmlink/rss-world"
    ],
    "south_america": [
        "https://www.batimes.com.ar/rss",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada",
        "https://www.nodal.am/feed/",
        "https://www1.folha.uol.com.br/mercado/rss091.xml",
        "https://www.americasquarterly.org/feed/"
    ]
}

def fetch_articles():
    recent_articles = []
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    for continent, feeds in rss_feeds.items():
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub_time = datetime(*entry.published_parsed[:6])
                if pub_time > one_hour_ago:
                    recent_articles.append((continent, entry.title, entry.summary))

    return recent_articles

def choose_article(articles, last_tweet_topic):
    # Filter articles present in multiple continents
    topic_count = {}
    for c, title, summary in articles:
        topic = title.lower().split(":")[0]
        if topic not in topic_count:
            topic_count[topic] = set()
        topic_count[topic].add(c)

    ranked = sorted(topic_count.items(), key=lambda x: (-len(x[1]), x[0] != last_tweet_topic))
    return ranked[0][0] if ranked else None

def create_tweet(topic):
    title = f"{topic.title()} Shocks World"
    body = f"{title}: A global development reported widely across regions. Stay tuned. #news"
    return body[:279]  # Ensure tweet fits

def main():
    print("✅ Nieuwsartikel ophalen...")
    articles = fetch_articles()
    if not articles:
        raise Exception("Geen geschikte artikelen gevonden")

    last_tweet_topic = os.getenv("LAST_TWEET_TOPIC", "")
    topic = choose_article(articles, last_tweet_topic)
    if not topic:
        raise Exception("Geen geschikt onderwerp gevonden")

    tweet_text = create_tweet(topic)
    try:
        print(f"📣 Tweet wordt geplaatst: {tweet_text}")
        api.update_status(tweet_text)
        print("✅ Tweet succesvol geplaatst!")
    except Exception as e:
        print(f"❌ Fout bij het plaatsen van de tweet: {e}")

if __name__ == "__main__":
    main()
