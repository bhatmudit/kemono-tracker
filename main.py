import requests
import time
import json
import os
from threading import Thread
from flask import Flask
import sys

print(f"Python version: {sys.version}")
print(f"Running on Render: {'RENDER' in os.environ}")

# Configuration
CREATORS = [
    {"service": "patreon", "id": "93759290", "name": "sleyca"},
    {"service": "patreon", "id": "48733767", "name": "torsten hewson"},
    {"service": "patreon", "id": "23356351", "name": "mathaz"},
]
CHECK_INTERVAL = 300  # 5 minutes
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
STORAGE_FILE = "/tmp/last_seen.json"  # Render ephemeral storage

print(f"Discord webhook URL from env: {DISCORD_WEBHOOK_URL}")  # DEBUG: Confirm webhook URL presence

app = Flask(__name__)

@app.route("/")
def home():
    return "Kemono Tracker Active - Last checked: " + time.ctime()

@app.route("/health")
def health():
    return {"status": "ok", "creators": len(CREATORS)}, 200

@app.route("/test_notify")
def test_notify():
    dummy_creator = {"service": "patreon", "id": "000", "name": "Test Creator"}
    dummy_post = {"id": "999", "title": "Test Post"}
    notify_discord(dummy_creator, dummy_post)
    return "Test notification sent"

def run_server():
    app.run(host="0.0.0.0", port=8080)

def get_latest_post(service, user_id):
    try:
        response = requests.get(
            f"https://kemono.su/api/v1/{service}/user/{user_id}",
            timeout=10
        )
        json_data = response.json()
        print(f"API response for {user_id}: {json_data}")  # DEBUG: Show raw API response
        return json_data[0] if json_data else None
    except Exception as e:
        print(f"API Error: {e}")
        return None

def check_creators():
    last_seen = load_data()
    print(f"Loaded last_seen data: {last_seen}")  # DEBUG: show loaded post IDs

    while True:
        for creator in CREATORS:
            post = get_latest_post(creator["service"], creator["id"])
            if not post:
                print(f"No posts found for {creator['name']}")
                continue

            print(f"Latest post for {creator['name']}: {post['id']} - {post['title']}")

            if last_seen.get(creator["id"]) != post["id"]:
                print(f"New post detected for {creator['name']}: {post['id']}")
                notify_discord(creator, post)
                last_seen[creator["id"]] = post["id"]
                save_data(last_seen)
            else:
                print(f"No new post for {creator['name']}")
        
        time.sleep(CHECK_INTERVAL)

def notify_discord(creator, post):
    print(f"Attempting to notify Discord about new post from {creator['name']}")
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook URL missing. Aborting notification.")
        return

    message = {
        "content": f"🆕 {creator['name']} posted: {post['title']}\n"
                  f"https://kemono.su/{creator['service']}/user/{creator['id']}/post/{post['id']}"
    }
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=message)
        print(f"Discord webhook sent: status {res.status_code}, response {res.text}")
    except Exception as e:
        print(f"Error sending Discord webhook: {e}")

def load_data():
    try:
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)
            print(f"Loaded last_seen data from file: {data}")
            return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def save_data(data):
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(data, f)
        print(f"Saved last_seen data: {data}")
    except Exception as e:
        print(f"Error saving data: {e}")

if __name__ == "__main__":
    print("Starting Kemono Tracker...")
    Thread(target=run_server, daemon=True).start()
    check_creators()
