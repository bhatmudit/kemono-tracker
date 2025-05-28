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

app = Flask(__name__)

@app.route("/")
def home():
    return "Kemono Tracker Active - Last checked: " + time.ctime()

@app.route("/health")
def health():
    return {"status": "ok", "creators": len(CREATORS)}, 200

def run_server():
    app.run(host="0.0.0.0", port=8080)

def get_latest_post(service, user_id):
    try:
        response = requests.get(
            f"https://kemono.su/api/v1/{service}/user/{user_id}",
            timeout=10
        )
        return response.json()[0] if response.json() else None
    except Exception as e:
        print(f"API Error: {e}")
        return None

def check_creators():
    last_seen = load_data()
    while True:
        for creator in CREATORS:
            post = get_latest_post(creator["service"], creator["id"])
            if not post:
                continue
                
            if last_seen.get(creator["id"]) != post["id"]:
                notify_discord(creator, post)
                last_seen[creator["id"]] = post["id"]
                save_data(last_seen)
        
        time.sleep(CHECK_INTERVAL)

def notify_discord(creator, post):
    if not DISCORD_WEBHOOK_URL:
        return
        
    message = {
        "content": f"🆕 {creator['name']} posted: {post['title']}\n"
                  f"https://kemono.su/{creator['service']}/user/{creator['id']}/post/{post['id']}"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=message)

def load_data():
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

if __name__ == "__main__":
    print("Starting Kemono Tracker...")
    Thread(target=run_server, daemon=True).start()
    check_creators()
