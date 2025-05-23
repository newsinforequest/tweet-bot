import requests
import feedparser
import openai
import os
import textwrap
from bs4 import BeautifulSoup

# Zet je OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_latest_article_from_rss():
    rss_url = "https://buitenland.headliner.nl/rss"
    feed = feedparser.parse(rss_url)

    if not feed.entries:
        raise Exception("Geen artikelen gevonden in de RSS-feed.")

    entry = feed.entries[0]
    article_url = entry.link
    article_page = requests.get(article_url)
    article_soup = BeautifulSoup(article_page.text, "html.parser")

    paragraphs = article_soup.find_all("p")
    full_text = " ".join(p.get_text() for p in paragraphs[:5])

    return full_text.strip(), article_url

def summarize_to_tweet(text, url):
    prompt = f"""
You are a social media expert. Summarize the following news article in your own words in English.
- The summary must be a tweet between 270 and 280 characters.
- Add a short clickbait title (max 5 words) before the tweet.
- Do not repeat content from the original directly.
- Mention the main topic clearly.
- Do not include hashtags or emojis.
- Use a neutral tone and avoid slang.
Text:
{text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    tweet = response["choices"][0]["message"]["content"].strip()
    tweet += f" {url}"
    return tweet

def main():
    print("✅ RSS-artikel ophalen...")
    article_text, article_url = get_latest_article_from_rss()

    print("🧠 Samenvatting genereren...")
    tweet = summarize_to_tweet(article_text, article_url)

    print("📢 Tweet gegenereerd:")
    print(textwrap.fill(tweet, width=100))

if __name__ == "__main__":
    main()
