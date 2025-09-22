# 🔍 Kemono Tracker // Decomissioned 

A simple Python script that checks for new posts from specific creators on [kemono.su](https://kemono.su) and notifies a Discord channel via webhook. Useful for fans who want instant updates from their favorite Patreon creators.

## ⚙️ Features

- Monitors multiple creators on Patreon via Kemono.
- Sends rich Discord notifications on new posts.
- Maintains state with `last_seen.json`.
- Supports GitHub Actions for automated hourly checks.
- Logs activity with rotation support.

## 🚀 Setup

1. Clone the repository and install dependencies:

```bash
pip install requests
```

2. Set your Discord webhook URL as an environment variable:

```bash
export DISCORD_WEBHOOK_URL="your_webhook_url"
```

3. Run the tracker manually:

```bash
python kemono_tracker.py
```

## 🤖 GitHub Actions Setup

To automate checks every hour, create a workflow file at `.github/workflows/kemono-tracker.yml`:

```yaml
name: Kemono Tracker

on:
  schedule:
    # Run every hour
    - cron: '0 * * * *'
  workflow_dispatch:  # Manual trigger
  push:
    branches: [ main ]
    paths: 
      - 'kemono_tracker.py'
      - '.github/workflows/kemono-tracker.yml'

jobs:
  track-updates:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests

    - name: Run Kemono tracker
      env:
        DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
      run: python kemono_tracker.py

    - name: Commit and push changes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add last_seen.json
        if git diff --staged --quiet; then
          echo "No changes to commit"
        else
          git commit -m "Update last seen posts [skip ci]"
          git push
```

📌 Don’t forget to add `DISCORD_WEBHOOK_URL` as a secret in your repository’s **Settings > Secrets and variables > Actions**.

## 📄 Logs

Logs are written to `tracker.log`. Old logs are trimmed automatically to keep size manageable.

## 📁 State Tracking

The file `last_seen.json` keeps track of the latest post IDs seen per creator. It's committed back to the repo during GitHub Action runs to persist state.

## 📬 Credits

Created by a fan to keep track of content updates.
