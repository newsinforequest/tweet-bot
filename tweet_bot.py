import feedparser
import random
from datetime import datetime, timedelta
import tweepy
import os
import openai

# Secrets uit GitHub Actions
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

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

def translate_to_english(text):
    try:
        prompt = f"Translate the following headline to English and expand it into a short tweet between 260 and 280 characters:\n\n\"{text}\"\n\nOnly return the tweet text."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        tweet = response.choices[0].message['content'].strip()
        return tweet
    except Exception as e:
        print(f"⚠️ Fout bij vertalen: {e}")
        return None

def select_article(articles, last_tweet=""):
    candidates = [title for title, continents in articles.items() if len(continents) >= 2]
    if candidates:
        return random.choice(candidates)
    elif articles:
        sorted_articles = sorted(articles.items(), key=lambda item: len(item[1]), reverse=True)
        top_titles = [t for t, v in sorted_articles if len(v) == len(sorted_articles[0][1])]
        return top_titles[0]
    return None

def tweet_article(api, text):
    tweet = translate_to_english(text)
    if not tweet:
        print("❌ Geen vertaling beschikbaar.")
        return
    tweet = tweet.replace('\n', ' ').replace('\r', '')
    length = len(tweet)
    if length < 260 or length > 280:
        print(f"⚠️ Tweetlengte ongeschikt ({length} tekens), overslaan.")
        return
    try:
        api.update_status(tweet)
        print(f"✅ Tweet geplaatst ({length} tekens): {tweet}")
    except Exception as e:
        print(f"⚠️ Tweet mislukt: {e}")

def authenticate():
    print("🔐 AUTH DEBUG INFO:")
    print("API_KEY set:", bool(API_KEY))
    print("API_SECRET set:", bool(API_SECRET))
    print("ACCESS_TOKEN set:", bool(ACCESS_TOKEN))
    print("ACCESS_TOKEN_SECRET set:", bool(ACCESS_TOKEN_SECRET))
    try:
        auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        api.verify_credentials()
        print("✅ Authenticated with Twitter.")
        return api
    except Exception as e:
        print("❌ Auth failed:", e)
        return None

def main():
    api = authenticate()
    if not api:
        return
    articles = fetch_articles()
    if not articles:
        print("❌ Geen artikelen gevonden.")
        return
    selected_title = select_article(articles)
    if selected_title:
        tweet_article(api, selected_title)
    else:
        print("❌ Geen geschikte tweet gevonden.")

if __name__ == "__main__":
    main()
