import requests
import time
import json
import os
from threading import Thread
from flask import Flask

CREATORS = [
    {"service": "patreon", "id": "93759290"},
    {"service": "patreon", "id": "48733767"},
    {"service": "patreon", "id": "23356351"},
]
CHECK_INTERVAL = 60  # seconds for test, change to 300 (5 min) later

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

STORAGE_FILE = "last_seen.json"

app = Flask("")

@app.route("/")
def home():
    return "Test Kemono Patreon Tracker is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def get_latest_post_id(service, creator_id):
    url = f"https://kemono.su/api/v1/{service}/user/{creator_id}"
    response = requests.get(url)
    response.raise_for_status()
    posts = response.json()
    if posts:
        return posts[0]["id"]
    return None

def load_last_seen():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_last_seen(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

def notify_discord(service, creator_id, post_id):
    if not DISCORD_WEBHOOK_URL:
        print("❌ Discord webhook URL not set!")
        return
    url = f"https://kemono.su/{service}/user/{creator_id}/post/{post_id}"
    content = {
        "content": f"🆕 New post from `{creator_id}` on `{service}`!\n{url}"
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=content)
    if response.status_code != 204:
        print(f"❌ Failed to send Discord message: {response.text}")
    else:
        print(f"✅ Discord notification sent for post {post_id}")

def monitor_creators():
    last_seen = load_last_seen()
    while True:
        for creator in CREATORS:
            service = creator["service"]
            cid = creator["id"]
            try:
                latest_id = get_latest_post_id(service, cid)
                if latest_id and last_seen.get(cid) != latest_id:
                    print(f"✅ New post for {cid}: {latest_id}")
                    notify_discord(service, cid, latest_id)
                    last_seen[cid] = latest_id
                    save_last_seen(last_seen)
                else:
                    print(f"⏳ No new post for {cid}")
            except Exception as e:
                print(f"⚠️ Error checking {cid}: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    monitor_creators()
