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

CREATOR_NAMES = {
    "93759290": "Sleyca",
    "48733767": "Torsten Hewson",
    "23356351": "Mathaz"
}

CHECK_INTERVAL = 3600  # check every hour

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

STORAGE_FILE = "last_seen.json"

app = Flask("")

@app.route("/")
def home():
    return "Kemono Patreon Tracker is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def get_latest_post(service, creator_id):
    url = f"https://kemono.su/api/v1/{service}/user/{creator_id}"
    response = requests.get(url)
    response.raise_for_status()
    posts = response.json()
    if posts:
        return posts[0]["id"], posts[0].get("title", "No Title")
    return None, None

def load_last_seen():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_last_seen(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

def notify_discord(content, mention_everyone=False):
    if not DISCORD_WEBHOOK_URL:
        print("❌ Discord webhook URL not set!")
        return

    payload = {
        "content": ("@everyone\n" if mention_everyone else "") + content,
        "allowed_mentions": {"parse": ["everyone"] if mention_everyone else []}
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"❌ Failed to send Discord message: {response.text}")
    else:
        print("✅ Discord message sent.")

def monitor_creators():
    last_seen = load_last_seen()

    while True:
        updates_found = False

        for creator in CREATORS:
            service = creator["service"]
            cid = creator["id"]
            name = CREATOR_NAMES.get(cid, cid)

            try:
                latest_id, title = get_latest_post(service, cid)
                if latest_id and last_seen.get(cid) != latest_id:
                    print(f"✅ New post for {name}: {title} ({latest_id})")
                    post_url = f"https://kemono.su/{service}/user/{cid}/post/{latest_id}"
                    message = f"🆕 New post from **{name}**!\n**{title}**\n{post_url}"
                    notify_discord(message, mention_everyone=True)
                    last_seen[cid] = latest_id
                    save_last_seen(last_seen)
                    updates_found = True
                else:
                    print(f"⏳ No new post for {name}")
            except Exception as e:
                print(f"⚠️ Error checking {name}: {e}")

        if not updates_found:
            notify_discord("✅ Kemono tracker ran successfully — no new posts found.", mention_everyone=False)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    monitor_creators()
