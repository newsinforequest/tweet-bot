import feedparser
import tweepy
import os
import datetime
import random
from time import sleep
from collections import Counter
from openai import OpenAI

# ✅ API-sleutels uit environment
client = OpenAI(api_key="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")

client_twitter = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
)

# 🌍 RSS-feeds per continent
FEEDS = {
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
        "https://www.lanacion.com.ar/rss-secties-politica/"
    ]
}

# 🆘 Fallback-feeds (gevalideerd)
FALLBACK_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://cnbc.com/id/100727362/device/rss/rss.html",
    "https://abcnews.go.com/abcnews/internationalheadlines",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.cbsnews.com/latest/rss/world",
    "https://www.france24.com/en/rss",
    "https://www.buzzfeed.com/world.xml",
    "https://www.nytimes.com/svc/collections/v1/publishers/nyt/world/index.xml",
    "https://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.foxnews.com/foxnews/latest",
    "https://www.dw.com/en/top-stories/s-9097/rss",
    "https://globalnews.ca/feed/",
    "https://www.cbc.ca/webfeed/rss/rss-world"
]

# 🧠 Thema fallback-feeds (evergreen topics)
THEME_FEEDS = {
    "Climate": ["https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "AI": ["https://spectrum.ieee.org/rss/artificial-intelligence/fulltext"],
    "Geopolitics": ["https://foreignpolicy.com/feed/"]
}

# 📅 Filter: maximaal 1 uur oud
def is_recent(entry):
    if not hasattr(entry, 'published_parsed'):
        return False
    pub_date = datetime.datetime(*entry.published_parsed[:6])
    return (datetime.datetime.utcnow() - pub_date) <= datetime.timedelta(hours=1)

# 🤖 Samenvatten tussen 260–280 tekens

def summarize_to_exact_length(text, min_len=260, max_len=280, max_attempts=5):
    for attempt in range(max_attempts):
        prompt = (
            f"Summarize the following news text in English in exactly one paragraph. "
            f"If the original summary is too short, intelligently add relevant context or implications to meet the length requirement.\n\n"
            f"Text:\n{text}\n\nSummary:"
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_len + 20
        )
        summary = response.choices[0].message.content.strip()
        length = len(summary)

        if min_len <= length <= max_len:
            print(f"✅ Samenvatting gelukt ({length} tekens)")
            return summary
        else:
            print(f"⏳ Poging {attempt + 1}: Samenvatting is {length} tekens lang, opnieuw proberen...")
            sle
