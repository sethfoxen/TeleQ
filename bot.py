import os
import asyncio
import json
import logging
import random
from telethon import TelegramClient, events, errors
from telethon.errors import FloodWaitError 
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define relative paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load configuration from config.json
config_path = os.path.join(BASE_DIR, "config.json")
try:
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "api_id": "your_api_id",  # Get it from https://my.telegram.org/apps
        "api_hash": "your_api_hash",  # Get it from https://my.telegram.org/apps
        "bot_token": "your_bot_token",  #Create your bot using BotFather
        "admin_id": 123456789,  # You can get yours using Get ID Bot '@get_id_bot'
        "channel_id": -1001234567890,  # Add Get ID Bot to your channel, and send a message, could also be the ID of a group/supergroup
        "forward_interval": 300,  # How often the bot posts to your channel, in seconds
        "debug_mode": False,  # Will print actions the script takes to the terminal
        "randomize_queue": False  # Picks a random message from the queue, instead of posting them in sequence
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    logging.info("Example config.json file created. Please update it with your credentials.")
    exit(1)

# Initialize message queue
queue_path = os.path.join(BASE_DIR, "message_queue.json")
try:
    with open(queue_path, "r") as f:
        message_queue = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    message_queue = []
    with open(queue_path, "w") as f:
        json.dump(message_queue, f)

# Initialize Telegram client
session_path = os.path.join(BASE_DIR, "bot.session")
client = TelegramClient(session_path, config["api_id"], config["api_hash"]).start(bot_token=config["bot_token"])

debug_mode = config.get("debug_mode", False)
channel_id = config.get("channel_id", None)
randomize_queue = config.get("randomize_queue", False)
empty_queue_notified = False  # Global flag to track whether the admin has been notified

def save_queue():
    try:
        with open(queue_path, "w") as f:
            json.dump(message_queue, f)
    except Exception as e:
        logging.error(f"Failed to save queue: {e}")

async def forward_messages():
    global message_queue, empty_queue_notified

    if not message_queue:
        if not empty_queue_notified:
            try:
                logging.info(f"Alerting admin of empty queue")
                await client.send_message(config["admin_id"], "Queue is empty.")
                empty_queue_notified = True  # Prevent repeated notifications
            except Exception as e:
                logging.error(f"Failed to notify admin about empty queue: {e}")
        return  # Exit early to avoid unnecessary API calls

    try:
        message_item = message_queue.pop(random.randint(0, len(message_queue) - 1) if randomize_queue else 0)

        if isinstance(message_item, list):  # Forwarding an album
            if debug_mode:
                logging.info(f"Forwarding album {message_item} to {channel_id} as a grouped message...")
            await client.forward_messages(entity=channel_id, messages=message_item, from_peer=config["admin_id"])
        else:  # Forwarding a single message
            if debug_mode:
                logging.info(f"Forwarding message ID {message_item} to {channel_id}...")
            await client.forward_messages(channel_id, message_item, config["admin_id"])

        save_queue()
        empty_queue_notified = False  # Reset flag since queue is not empty

    except errors.FloodWaitError as e:
        logging.warning(f"Rate limit reached. Sleeping for {e.seconds + 60} seconds.")
        await asyncio.sleep(e.seconds + 60)
    except errors.RPCError as e:
        logging.error(f"Failed to forward message: {e}, network issue?")
        if message_item is not None:
            message_queue.insert(0, message_item)  # Only retry if message exists
            save_queue()
    except Exception as e:
        logging.error(f"Unexpected error forwarding message: {e}")
        if message_item is not None:  # Prevents undefined reference
            if "message not found" in str(e).lower():  # Handle deleted messages gracefully
                logging.warning(f"Skipping deleted or unavailable message: {message_item}")
                # Remove the deleted message from the queue
                message_queue = [msg_id for msg_id in message_queue if msg_id != message_item]  # Remove message
                save_queue()  # Save the updated queue after removal
            else:
                message_queue.insert(0, message_item)  # Only retry if the error is recoverable
                save_queue()

# Temporary storage for grouped messages before forwarding
grouped_messages_buffer = defaultdict(list)

@client.on(events.NewMessage)
async def handle_new_message(event):
    try:
        sender_id = event.sender_id

        # Reject messages from non-admins
        if sender_id != config["admin_id"]:
            await event.respond("You're not an admin! IGNORED")
            if debug_mode:
                logging.info(f"Ignored message from non-admin {sender_id}")
            return  # Stop processing

        if event.is_private and not event.message.out:
            if event.text and event.text.startswith("/"):
                if event.text.lower() == "/ping":
                    await event.respond("pong")
                    if debug_mode:
                        logging.info(f"Command received: {event.text}")
                elif event.text.lower() == "/queue":
                    queue_size = len(message_queue)
                    await event.respond(f"Queue has {queue_size} item(s).")
                    if debug_mode:
                        logging.info(f"Command received: {event.text}")
                elif event.text.lower() == "/clearqueue":
                    message_queue.clear()
                    save_queue()
                    await event.respond("Queue cleared.")
                    if debug_mode:
                        logging.info(f"Command received: {event.text}")
                else:
                    await event.respond("Unknown command. Available commands: /ping, /queue, /clearqueue")
                    if debug_mode:
                        logging.info(f"Unknown command received: {event.text}")
                return  # Ensure commands do not get added to the queue

            grouped_id = event.message.grouped_id

            if grouped_id:
                if debug_mode:
                    logging.info(f"Detected grouped message: {grouped_id}")

                # Store message in the buffer
                grouped_messages_buffer[grouped_id].append(event.message.id)

                # Schedule processing if not already scheduled
                if len(grouped_messages_buffer[grouped_id]) == 1:
                    asyncio.create_task(process_grouped_messages(grouped_id))  # Handle album asynchronously

            else:
                message_queue.append(event.message.id)  # Store single messages normally
                save_queue()
                empty_queue_notified = False
                if debug_mode:
                    logging.info(f"Added message ID {event.message.id} from admin {sender_id} to queue")

    except Exception as e:
        logging.error(f"Error handling message from {sender_id}: {e}")

async def process_grouped_messages(grouped_id):
    await asyncio.sleep(2)  # Small delay to ensure all album messages arrive
    if grouped_id in grouped_messages_buffer and grouped_messages_buffer[grouped_id]:
        if debug_mode:
            logging.info(f"Stored album (group_id={grouped_id}) with messages {grouped_messages_buffer[grouped_id]} in queue")
        message_queue.append(grouped_messages_buffer.pop(grouped_id))
        save_queue()
        empty_queue_notified = False
    elif debug_mode:
        logging.warning(f"Skipping empty album {grouped_id}")

async def main():
    try:
        while True:
            await forward_messages()  # Always run forward_messages(), even if the queue is empty
            await asyncio.sleep(config["forward_interval"])  # Sleep after checking queue
    except (errors.FloodWaitError, errors.RPCError) as e:
        logging.warning(f"API error occurred: {e}. Retrying in 60 seconds.")
        await asyncio.sleep(60)
    except ConnectionError:
        logging.warning("Lost internet connection. Retrying in 60 seconds...")
        await asyncio.sleep(60)
    except asyncio.CancelledError:
        logging.info("Main loop cancelled.")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")
    finally:
        logging.info("Exiting main loop gracefully.")

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
finally:
    if not loop.is_closed():
        loop.close()
        