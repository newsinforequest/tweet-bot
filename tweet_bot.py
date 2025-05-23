import requests
import feedparser
import openai
import os
import textwrap
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# Zet je OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Wereldwijde RSS-feeds per continent
rss_feeds = {
    "Europe": ["https://www.theguardian.com/world/rss", "https://www.dw.com/en/top-stories/s-9097/rss"],
    "North America": ["http://rss.cnn.com/rss/edition.rss", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"],
    "Asia": ["https://www.scmp.com/rss/91/feed", "https://www.aljazeera.com/xml/rss/all.xml"],
    "Africa": ["https://www.news24.com/rss", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"],
    "South America": ["https://www.batimes.com.ar/rss", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada"],
    "Oceania": ["https://www.abc.net.au/news/feed/51120/rss.xml"],
}

def get_recent_articles(hours=2):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for region, feeds in rss_feeds.items():
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                pub_date = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6], tzinfo=timezone.utc)
                    if pub_datetime > since:
                        articles.append({
                            "title": entry.title,
                            "summary": entry.get("summary", ""),
                            "link": entry.link,
                            "region": region
                        })

    return articles

def find_common_topics(articles):
    from collections import defaultdict
    topic_map = defaultdict(list)
    for article in articles:
        key = article["title"].split(":")[0].strip().lower()
        topic_map[key].append(article)

    # Filter onderwerpen die op minstens 2 continenten verschijnen
    valid_topics = []
    for topic, grouped in topic_map.items():
        regions = set([a["region"] for a in grouped])
        if len(regions) >= 2:
            valid_topics.append(grouped)

    return valid_topics

def summarize_topic_to_tweet(topic_articles):
    text = " ".join(a["summary"] for a in topic_articles)
    urls = [a["link"] for a in topic_articles]
    prompt = f"""
You are a social media expert. Summarize this global news topic in a single English tweet.
- The tweet must be between 270–280 characters.
- Start with a clickbait title (max 5 words).
- Use original wording.
- Emphasize that this topic appears across continents.
Text:
{text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    tweet = response["choices"][0]["message"]["content"].strip()
    tweet += f" {urls[0]}"
    return tweet

def main():
    print(f"
🌍 Start éénmalige tweet - {datetime.now().isoformat(timespec='minutes')}")
    try:
        articles = get_recent_articles()
        common_topics = find_common_topics(articles)
        if not common_topics:
            print("⚠️ Geen gedeelde onderwerpen gevonden.")
            return
        tweet = summarize_topic_to_tweet(common_topics[0])
        print("📢 Tweet:")
        print(textwrap.fill(tweet, width=100))
    except Exception as e:
        print(f"❌ Fout tijdens uitvoeren: {e}")

if __name__ == "__main__":
    main()
