import asyncio
import json
import logging
import random
from telethon import TelegramClient, events, errors

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from config.json
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "api_id": "your_api_id",  # Get it from https://my.telegram.org/apps
        "api_hash": "your_api_hash",  # Get it from https://my.telegram.org/apps
        "bot_token": "your_bot_token",  #Create your bot using BotFather
        "admin_id": 123456789,  #You can get yours using Get ID Bot '@get_id_bot'
        "channel_id": -1001234567890,  #Add Get ID Bot to your channel, and send a message, could also be the ID of a group/supergroup
        "forward_interval": 60,  #How often the bot posts to your channel, in seconds
        "debug_mode": False,  #Will print actions the script takes to the terminal
        "randomize_queue": False  #Picks a random message from the queue, instead of posting them in sequence
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    logging.info("Example config.json file created. Please update it with your credentials.")
    exit(1)

# Initialize message queue
try:
    with open("message_queue.json", "r") as f:
        message_queue = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    message_queue = []
    with open("message_queue.json", "w") as f:
        json.dump(message_queue, f)

# Initialize Telegram client
client = TelegramClient("bot", config["api_id"], config["api_hash"]).start(bot_token=config["bot_token"])

debug_mode = config.get("debug_mode", False)
channel_id = config.get("channel_id", None)
randomize_queue = config.get("randomize_queue", False)

def save_queue():
    try:
        with open("message_queue.json", "w") as f:
            json.dump(message_queue, f)
    except Exception as e:
        logging.error(f"Failed to save queue: {e}, does your user have write permissions?")

async def forward_messages():
    global message_queue
    try:
        if message_queue and channel_id:
            if randomize_queue:
                random.shuffle(message_queue)
            if debug_mode:
                logging.info(f"Forwarding 1 message to {channel_id}...")
            message_id = message_queue.pop(0)
            try:
                await client.forward_messages(channel_id, message_id, config["admin_id"])
            except errors.FloodWait as e:
                logging.warning(f"Rate limit reached. Sleeping for {e.seconds + 60} seconds.")
                message_queue.insert(0, message_id)  # Reinsert message in case of failure
                save_queue()
                await asyncio.sleep(e.seconds + 60)
            except errors.RPCError as e:
                logging.error(f"Failed to forward message ID {message_id}: {e}, is the internet down?")
                message_queue.insert(0, message_id)  # Reinsert message in case of failure
                save_queue()
            except Exception as e:
                logging.error(f"Unexpected error forwarding message {message_id}: {e}")
                message_queue.insert(0, message_id)  # Reinsert message in case of failure
                save_queue()
    except Exception as e:
        logging.error(f"Error in forward_messages: {e}")

@client.on(events.NewMessage)
async def handle_new_message(event):
    try:
        if event.is_private and not event.message.out:
            message_queue.append(event.message.id)
            save_queue()
            if debug_mode:
                logging.info(f"Added new message ID {event.message.id} to queue")
    except Exception as e:
        logging.error(f"Error handling new message: {e}")

async def main():
    try:
        while True:
            try:
                await forward_messages()
            except (errors.FloodWait, errors.RPCError) as e:
                logging.warning(f"Error occurred, retrying after 60 seconds: {e}")
                await asyncio.sleep(60)
            await asyncio.sleep(config["forward_interval"])
    except asyncio.CancelledError:
        logging.info("Main loop cancelled.")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")

async def shutdown():
    try:
        logging.info("Shutting down gracefully...")
        await client.disconnect()
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except (KeyboardInterrupt, SystemExit):
    logging.info("Received exit signal, shutting down...")
    loop.run_until_complete(shutdown())
except Exception as e:
    logging.error(f"Fatal error: {e}")
finally:
    loop.close()
