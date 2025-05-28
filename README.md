# kemono-tracker
I just had LLM's make me a kemono tracker

Monitors Kemono.su for new posts and sends Discord notifications.

## Render Deployment

1. Connect your GitHub account
2. Create new Web Service
3. Configure:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. Set environment variable:
   - `DISCORD_WEBHOOK_URL`: Your Discord webhook URL
5. Deploy!

The service will automatically restart if it crashes.
