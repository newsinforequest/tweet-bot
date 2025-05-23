# Global News Tweet Bot (10x/day)

This bot uses OpenAI's GPT-4 to generate realistic, globally relevant news summaries with clickbait titles, and posts 10 tweets per day spaced evenly over 24 hours via GitHub Actions.

## ✅ Features
- English tweets
- Clickbait-style short headlines (max 6 words)
- Global news summaries (240–280 characters)
- Posts 10x/day automatically via GitHub Actions

## 🛠 Setup Instructions

1. Fork or upload this repo to your GitHub account.
2. Go to your repo → Settings → Secrets and Variables → Actions → "New repository secret".
   Add the following secrets:

- `OPENAI_API_KEY`
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_SECRET`

3. GitHub Actions will run this daily at midnight (UTC) and post 10 tweets across the next 24 hours.

## 🔐 Safety

- No user data is collected.
- You stay within the free tier of Twitter's API (max 1,500 tweets/month).

## 📦 Dependencies

- `openai`
- `tweepy`
