import requests
from bs4 import BeautifulSoup
import openai
import os
import textwrap

# Zet je OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_latest_headliner_article():
    url = "https://buitenland.headliner.nl/"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Kon de pagina niet laden: status", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    # Zoek het eerste artikel via herkenbare tekst-structuur
    article_links = soup.find_all("a", href=True)
    for link in article_links:
        href = link["href"]
        if href.startswith("/artikel/"):
            article_url = "https://buitenland.headliner.nl" + href
            article_page = requests.get(article_url)
            article_soup = BeautifulSoup(article_page.text, "html.parser")
            paragraphs = article_soup.find_all("p")
            full_text = " ".join(p.get_text() for p in paragraphs[:5])  # Max 5 alinea's
            return full_text.strip(), article_url

    raise Exception("Geen geschikte artikelen gevonden op buitenland.headliner.nl")

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
    print("✅ Nieuwsartikel ophalen...")
    article_text, article_url = get_latest_headliner_article()

    print("🧠 Samenvatting genereren...")
    tweet = summarize_to_tweet(article_text, article_url)

    print("📢 Tweet gegenereerd:")
    print(textwrap.fill(tweet, width=100))

if __name__ == "__main__":
    main()
