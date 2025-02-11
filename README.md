# DISCLAIMER: The majority of this code was generated using ChatGPT
# TeleQ: Telegram Queue Bot

## Description
This bot automatically forwards messages sent to it in a private chat to a specified Telegram channel at a set interval. Messages are stored in a persistent queue, ensuring that they aren't lost even if the bot restarts. There are options to include randomizing the queue order, error handling for API limits and connection issues, and admin-configurable settings. You'll need to create an app on https://my.telegram.org/ by clicking "API development tools" and signing in using your Telegram account in order to get your API ID and hash.

## Requirements
- Python 3.8+, 3.11+ preferred
- Required dependencies (listed in `requirements.txt`)
- A Telegram bot API token
- A Telegram API ID and API hash (https://my.telegram.org/)
- A channel ID where messages will be forwarded

## Installation
1. Clone this repository or download the script.
2. Install dependencies using pip:
   ```sh
   pip install -r requirements.txt
   ```
3. Create a `config.json` file in the same directory as the script. The bot will generate an example file if it does not exist.
4. Edit `config.json` with your bot credentials and preferences.

## Configuration
Modify `config.json` to configure the bot:
```json
{
    "api_id": 1234567,
    "api_hash": "your_api_hash",
    "bot_token": "your_bot_token",
    "admin_id": 123456789,
    "channel_id": -1001234567890,
    "forward_interval": 60,
    "debug_mode": false,
    "randomize_queue": false
}
```
### Settings:
- **`api_id`** & **`api_hash`**: Required for the Telegram API. (https://my.telegram.org/)
- **`bot_token`**: The bot's API token.
- **`admin_id`**: Your Telegram user ID (to identify the admin).
- **`channel_id`**: The ID of the channel where messages should be forwarded.
- **`forward_interval`**: How often (in seconds) a message is forwarded.
- **`debug_mode`**: Enables detailed logging when set to `true`.
- **`randomize_queue`**: If `true`, messages will be forwarded in random order.

## Usage
Run the bot with:
```sh
python telegram_queue_bot.py
```

### Sending Messages to the Bot
- Send any message (text, image, video, etc.) to the bot in a private chat.
- The bot will store the message ID in the queue.
- At the configured interval, the bot will forward one message at a time to the configured channel.

### Stopping the Bot
- Press `CTRL+C` to exit.
- The bot will shut down gracefully, ensuring that no messages are lost.

## Error Handling
- If the bot reaches the Telegram API limit, it will wait for the required cooldown period plus an additional 60 seconds before retrying.
- If the bot loses internet connection, it will retry every 60 seconds until reconnected.
- Any errors will be logged for debugging.
