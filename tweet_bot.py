import openai
import tweepy
import time
import random
import os
from datetime import datetime

# OpenAI API-sleutel uit GitHub Secrets
openai.api_key = os.environ['OPENAI_API_KEY']

# Twitter API-sleutels uit GitHub Secrets
consumer_key = os.environ['TWITTER_API_KEY']
consumer_secret = os.environ['TWITTER_API_SECRET']
access_token = os.environ['TWITTER_ACCESS_TOKEN']
access_token_secret = os.environ['TWITTER_ACCESS_SECRET']

auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)

def genereer_tweet():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        f"As of {timestamp}, summarize one recent and globally relevant news story in English. "
        "Write a short, clickbait-style title (max 6 words), followed by a newline and a 240–280 character summary. "
        "Make it informative and realistic, as if it's breaking news."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return response['choices'][0]['message']['content'].strip()

# 10 tweets per dag verspreid over 24 uur (~2,5 uur tussen)
for i in range(10):
    try:
        tweet = genereer_tweet()
        api.update_status(tweet)
        print(f"Tweet {i+1} geplaatst.")
        time.sleep(random.randint(8700, 9300))  # 2 uur 25 min – 2 uur 35 min
    except Exception as e:
        print(f"Fout bij tweet {i+1}: {e}")
        time.sleep(60)
