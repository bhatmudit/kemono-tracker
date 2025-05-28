# 🔍 Kemono Tracker

A Python script that tracks creators on [kemono.su](https://kemono.su) and notifies via Discord when new posts appear.

## ✅ Features

- Monitors specific creator IDs
- Sends new post alerts to Discord
- Alerts on high failure rates or save issues
- Keeps log files with auto-trimming
- Designed for GitHub Actions automation

## ⚙️ Setup

1. **Install requirements**

```bash
pip install requests
```

2. **Set Discord webhook**

```bash
export DISCORD_WEBHOOK_URL="your_webhook_url"
```

3. **Run the script**

```bash
python tracker.py
```

## 🤖 GitHub Actions

Example workflow:

```yaml
- uses: actions/checkout@v3
- uses: actions/setup-python@v4
  with: { python-version: '3.11' }
- run: pip install requests
- run: python tracker.py
```

Include `DISCORD_WEBHOOK_URL` as a GitHub secret.

## 🔧 Config

Edit `CREATORS` and `CREATOR_NAMES` in `tracker.py` to match the creators you want to track.

---

MIT License
