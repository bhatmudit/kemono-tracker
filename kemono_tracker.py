import requests
import json
import os
import time
from typing import Dict, List, Optional, Tuple

# Configuration
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

# Constants
KEMONO_BASE_URL = "https://kemono.su/api/v1"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
STORAGE_FILE = "last_seen.json"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 2  # seconds between requests
DISCORD_SUCCESS_STATUS = 204

# Headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KemonoTracker/1.0)"
}


def get_latest_post(service: str, creator_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Get the latest post ID and title for a creator."""
    url = f"{KEMONO_BASE_URL}/{service}/user/{creator_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        posts = response.json()
        
        if posts and len(posts) > 0:
            latest_post = posts[0]
            return latest_post.get("id"), latest_post.get("title", "No Title")
        return None, None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error for {creator_id}: {e}")
        return None, None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"❌ Data parsing error for {creator_id}: {e}")
        return None, None


def load_last_seen() -> Dict[str, str]:
    """Load the last seen post IDs from storage."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Error loading storage file: {e}")
    return {}


def save_last_seen(data: Dict[str, str]) -> None:
    """Save the last seen post IDs to storage."""
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"❌ Error saving storage file: {e}")


def notify_discord(content: str, mention_everyone: bool = False) -> bool:
    """Send a notification to Discord. Returns True if successful."""
    if not DISCORD_WEBHOOK_URL:
        print("❌ Discord webhook URL not set!")
        return False

    payload = {
        "content": ("@everyone\n" if mention_everyone else "") + content,
        "allowed_mentions": {"parse": ["everyone"] if mention_everyone else []}
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            json=payload, 
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == DISCORD_SUCCESS_STATUS:
            print("✅ Discord message sent.")
            return True
        else:
            print(f"❌ Discord webhook failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Discord notification error: {e}")
        return False


def check_creator_updates(last_seen: Dict[str, str]) -> List[Dict]:
    """Check all creators for updates and return a list of new posts."""
    new_posts = []
    
    for i, creator in enumerate(CREATORS):
        # Rate limiting delay (except for first request)
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)
            
        service = creator["service"]
        cid = creator["id"]
        name = CREATOR_NAMES.get(cid, f"Creator {cid}")

        latest_id, title = get_latest_post(service, cid)
        
        if latest_id is None:
            print(f"⚠️ Could not check {name}")
            continue
            
        if last_seen.get(cid) != latest_id:
            print(f"✅ New post for {name}: {title} ({latest_id})")
            post_url = f"https://kemono.su/{service}/user/{cid}/post/{latest_id}"
            
            new_posts.append({
                "creator_id": cid,
                "creator_name": name,
                "post_id": latest_id,
                "title": title,
                "url": post_url
            })
            
            last_seen[cid] = latest_id
        else:
            print(f"⏳ No new post for {name}")
    
    return new_posts


def send_notifications(new_posts: List[Dict]) -> None:
    """Send Discord notifications for new posts."""
    for post in new_posts:
        message = (
            f"🆕 New post from **{post['creator_name']}**!\n"
            f"**{post['title']}**\n"
            f"{post['url']}"
        )
        notify_discord(message, mention_everyone=True)
        # Small delay between Discord messages to avoid rate limiting
        time.sleep(1)


def monitor_creators_once() -> None:
    """Main function to check for updates and send notifications."""
    print("🔍 Starting Kemono tracker...")
    
    last_seen = load_last_seen()
    new_posts = check_creator_updates(last_seen)
    
    if new_posts:
        print(f"📢 Found {len(new_posts)} new post(s), sending notifications...")
        send_notifications(new_posts)
    else:
        print("✅ No new posts found.")
        # Only send "no updates" message in CI environment
        if os.getenv("GITHUB_ACTIONS"):
            notify_discord("✅ Kemono tracker ran successfully — no new posts found.")
    
    save_last_seen(last_seen)
    print("💾 State saved. Tracking complete.")


if __name__ == "__main__":
    monitor_creators_once()
