import requests
import json
import os
import time
import logging
from datetime import datetime
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
LOG_FILE = "tracker.log"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 2  # seconds between requests
DISCORD_SUCCESS_STATUS = 204
MAX_RETRIES = 3
RETRY_DELAY = 5

# Headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KemonoTracker/1.0)"
}

# Setup logging
def setup_logging():
    """Configure logging to both file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log_stats(stats: Dict) -> None:
    """Log run statistics."""
    logging.info(f"📊 Run Statistics:")
    logging.info(f"   • Creators checked: {stats['creators_checked']}")
    logging.info(f"   • New posts found: {stats['new_posts']}")
    logging.info(f"   • Errors encountered: {stats['errors']}")
    logging.info(f"   • Runtime: {stats['runtime']:.2f}s")

def get_latest_post_with_retry(service: str, creator_id: str, retries: int = MAX_RETRIES) -> Tuple[Optional[str], Optional[str]]:
    """Get the latest post ID and title for a creator with retry logic."""
    url = f"{KEMONO_BASE_URL}/{service}/user/{creator_id}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            posts = response.json()
            
            if posts and len(posts) > 0:
                latest_post = posts[0]
                post_id = latest_post.get("id")
                title = latest_post.get("title", "No Title")
                
                # Validate post data
                if not post_id:
                    logging.warning(f"⚠️ Post missing ID for creator {creator_id}")
                    return None, None
                    
                return str(post_id), title
            
            logging.info(f"📭 No posts found for creator {creator_id}")
            return None, None
            
        except requests.exceptions.Timeout:
            logging.warning(f"⏰ Timeout for {creator_id} (attempt {attempt + 1}/{retries})")
        except requests.exceptions.RequestException as e:
            logging.warning(f"🌐 Network error for {creator_id} (attempt {attempt + 1}/{retries}): {e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logging.error(f"📄 Data parsing error for {creator_id}: {e}")
            break  # Don't retry parsing errors
        
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY)
    
    logging.error(f"❌ Failed to get posts for creator {creator_id} after {retries} attempts")
    return None, None

def load_last_seen() -> Dict[str, str]:
    """Load the last seen post IDs from storage."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"📂 Loaded {len(data)} creator states from storage")
                return data
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"💾 Error loading storage file: {e}")
    
    logging.info("📂 No existing storage found, starting fresh")
    return {}

def save_last_seen(data: Dict[str, str]) -> bool:
    """Save the last seen post IDs to storage."""
    try:
        # Create backup of existing file
        if os.path.exists(STORAGE_FILE):
            backup_file = f"{STORAGE_FILE}.backup"
            os.rename(STORAGE_FILE, backup_file)
        
        with open(STORAGE_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"💾 Saved {len(data)} creator states to storage")
        return True
        
    except IOError as e:
        logging.error(f"💾 Error saving storage file: {e}")
        return False

def notify_discord(content: str, mention_everyone: bool = False, is_error: bool = False) -> bool:
    """Send a notification to Discord."""
    if not DISCORD_WEBHOOK_URL:
        logging.error("🔗 Discord webhook URL not configured!")
        return False

    # Add error styling
    if is_error:
        content = f"🚨 **KEMONO TRACKER ERROR** 🚨\n{content}"

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
            logging.info("📨 Discord notification sent successfully")
            return True
        else:
            logging.error(f"📨 Discord webhook failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logging.error(f"📨 Discord notification error: {e}")
        return False

def check_creator_updates(last_seen: Dict[str, str]) -> Tuple[List[Dict], Dict]:
    """Check all creators for updates and return new posts + statistics."""
    new_posts = []
    stats = {
        'creators_checked': 0,
        'new_posts': 0,
        'errors': 0,
        'skipped': 0
    }
    
    for i, creator in enumerate(CREATORS):
        # Rate limiting delay (except for first request)
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)
            
        service = creator["service"]
        cid = creator["id"]
        name = CREATOR_NAMES.get(cid, f"Creator {cid}")
        
        stats['creators_checked'] += 1
        logging.info(f"🔍 Checking {name} ({service}/{cid})")

        latest_id, title = get_latest_post_with_retry(service, cid)
        
        if latest_id is None:
            stats['errors'] += 1
            continue
            
        # Check if this is a new post
        if last_seen.get(cid) != latest_id:
            # Check if this is the first time tracking this creator
            if cid not in last_seen:
                logging.info(f"🆕 First time tracking {name}, setting baseline")
                last_seen[cid] = latest_id
                stats['skipped'] += 1
                continue
            
            logging.info(f"✨ New post found for {name}: {title}")
            post_url = f"https://kemono.su/{service}/user/{cid}/post/{latest_id}"
            
            new_posts.append({
                "creator_id": cid,
                "creator_name": name,
                "post_id": latest_id,
                "title": title,
                "url": post_url,
                "service": service
            })
            
            last_seen[cid] = latest_id
            stats['new_posts'] += 1
        else:
            logging.info(f"⏳ No new posts for {name}")
    
    return new_posts, stats

def send_notifications(new_posts: List[Dict]) -> int:
    """Send Discord notifications for new posts."""
    successful = 0
    
    for post in new_posts:
        # Create rich message with more details
        message = (
            f"🆕 **New {post['service'].title()} Post!**\n"
            f"👤 **Creator**: {post['creator_name']}\n"
            f"📝 **Title**: {post['title']}\n"
            f"🔗 **Link**: {post['url']}\n"
            f"⏰ **Found**: {datetime.now().strftime('%H:%M UTC')}"
        )
        
        if notify_discord(message, mention_everyone=True):
            successful += 1
        
        # Small delay between Discord messages
        time.sleep(1)
    
    return successful

def send_failure_alert(error_details: str) -> None:
    """Send failure alert to Discord."""
    message = (
        f"❌ **Tracker encountered errors:**\n"
        f"```\n{error_details}\n```\n"
        f"⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"🔧 **Check logs for more details**"
    )
    notify_discord(message, mention_everyone=False, is_error=True)

def cleanup_old_logs(max_lines: int = 10000) -> None:
    """Keep log file from getting too large."""
    if not os.path.exists(LOG_FILE):
        return
        
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) > max_lines:
            # Keep last 75% of lines
            keep_lines = int(max_lines * 0.75)
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines[-keep_lines:])
            logging.info(f"🧹 Trimmed log file to {keep_lines} lines")
            
    except IOError as e:
        logging.warning(f"🧹 Could not trim log file: {e}")

def monitor_creators_once() -> None:
    """Main function to check for updates and send notifications."""
    start_time = time.time()
    setup_logging()
    
    logging.info("🚀 Starting Kemono tracker...")
    logging.info(f"📊 Monitoring {len(CREATORS)} creators")
    
    # Cleanup old logs
    cleanup_old_logs()
    
    try:
        # Load previous state
        last_seen = load_last_seen()
        
        # Check for updates
        new_posts, stats = check_creator_updates(last_seen)
        
        # Calculate runtime
        stats['runtime'] = time.time() - start_time
        
        # Process results
        if new_posts:
            logging.info(f"🎉 Found {len(new_posts)} new post(s)!")
            successful_notifications = send_notifications(new_posts)
            
            if successful_notifications < len(new_posts):
                logging.warning(f"⚠️ Only {successful_notifications}/{len(new_posts)} notifications sent successfully")
        
        # Save updated state
        if not save_last_seen(last_seen):
            error_msg = "Failed to save state - notifications may repeat next run"
            logging.error(f"💾 {error_msg}")
            send_failure_alert(error_msg)
        
        # Log final statistics
        log_stats(stats)
        
        # Send failure alert if significant errors occurred
        if stats['errors'] > len(CREATORS) * 0.5:  # More than 50% failed
            error_msg = f"High failure rate: {stats['errors']}/{stats['creators_checked']} creators failed"
            send_failure_alert(error_msg)
        
        logging.info("✅ Kemono tracker completed successfully")
        
    except Exception as e:
        error_msg = f"Unexpected error in main function: {str(e)}"
        logging.error(f"💥 {error_msg}")
        send_failure_alert(error_msg)
        raise

if __name__ == "__main__":
    monitor_creators_once()
