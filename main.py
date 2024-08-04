import telegram.ext
import re
from dotenv import load_dotenv
import os
import logging
import json
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv('TOKEN')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# File to store chat IDs
chat_id_file = 'chat_ids.json'

# Load chat IDs from file
if os.path.exists(chat_id_file):
    with open(chat_id_file, 'r') as file:
        chat_ids = set(json.load(file))
else:
    chat_ids = set()

# Admin chat ID for restricted access to broadcast command
admin_chat_ids = {1548840421}  # Replace with actual admin chat ID

# Function to save chat IDs to file
def save_chat_ids():
    with open(chat_id_file, 'w') as file:
        json.dump(list(chat_ids), file)

def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in chat_ids:
        chat_ids.add(chat_id)
        save_chat_ids()

    user_mention = update.message.from_user.mention_html()
    start_message = (
        f"Hey {user_mention}! I'm here to help you keep your channel's captions clean and tidy.\n\n"
        "Just add me as an admin to your channel, and I'll automatically remove any links, mentions, and their preceding lines from your posts.\n"
        "Checkout /help to Read More."
    )
    update.message.reply_text(start_message, parse_mode='HTML')

def help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    user_mention = update.message.from_user.mention_html()
    help_text = (
        f"Welcome {user_mention} to ADAM THE ONE Bot! Here's how I can assist you:\n\n"
        "•   To begin, add me to your channel as an admin so I can help manage captions.\n"
        "•   Once added, send me any post with a link or mention, and I'll remove the link or mention and the preceding line to keep your captions clean and tidy!\n\n"
        "/start - Start the bot and receive a friendly greeting.\n"
        "/help - Get detailed instructions on how to use the bot.\n"
        "/subscribe - Subscribe to receive broadcast messages.\n"
        "\nFeel free to explore and let me know how I can assist you better!"
    )
    update.message.reply_text(help_text, parse_mode='HTML')

def escape_markdown_v2(text: str) -> str:
    # Escape special characters for MarkdownV2
    escape_chars = r'\_*[]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def edit_caption(update: Update, context: CallbackContext) -> None:
    # Check if the update is from a channel post or DM
    if update.channel_post:
        original_caption = update.channel_post.caption
        media = update.channel_post
        chat_id = update.channel_post.chat_id
        message_id = update.channel_post.message_id
    elif update.message:
        original_caption = update.message.caption
        media = update.message
        chat_id = update.message.chat_id
        message_id = update.message.message_id
    else:
        return

    if original_caption:
        lines = original_caption.split('\n')
        new_caption = []
        skip_next_line = False

        for i in range(len(lines)):
            line = lines[i]
            if i == 0:
                # Replace dots (.) with spaces ( ) except before 'mkv' in the first line
                line = re.sub(r'\.(?!(mkv\b))', ' ', line)
            if 'http' in line:
                if i > 0 and not ('http' in lines[i - 1] or '@' in lines[i - 1]):
                    # Remove the preceding line if it's not a link or mention
                    new_caption.pop()
                skip_next_line = True
                continue
            if '@' in line:
                # Remove the entire line containing the mention
                if i == 0:
                    # If the mention is in the first line, remove only the mention with surrounding characters
                    line = re.sub(r'[\.\(\[\{\s]*@\w+[\.\)\]\}\s]*', '', line).strip()
                    if line:
                        new_caption.append(line)
                continue
            # Replace underscores (_) with spaces ( ) in the caption
            line = line.replace('_', ' ')

            if skip_next_line:
                skip_next_line = False
                continue
            new_caption.append(line)

        edited_caption = '\n'.join(new_caption)

        # Escape special characters for MarkdownV2
        escaped_caption = escape_markdown_v2(edited_caption)

        # Format the caption based on media type
        if media.photo:
            formatted_caption = f"_*{escaped_caption}*_"
        else:
            formatted_caption = f"*{escaped_caption}*"

        if update.channel_post:
            # Edit caption in channel posts
            context.bot.edit_message_caption(chat_id=chat_id,
                                             message_id=message_id,
                                             caption=formatted_caption,
                                             parse_mode=ParseMode.MARKDOWN_V2)
        elif update.message:
            # Respond with edited caption in DMs
            if media.photo:
                context.bot.send_photo(chat_id=chat_id,
                                       photo=media.photo[-1].file_id,
                                       caption=formatted_caption,
                                       parse_mode=ParseMode.MARKDOWN_V2,
                                       reply_to_message_id=message_id)  # Threaded reply
            elif media.video:
                context.bot.send_video(chat_id=chat_id,
                                       video=media.video.file_id,
                                       caption=formatted_caption,
                                       parse_mode=ParseMode.MARKDOWN_V2,
                                       reply_to_message_id=message_id)  # Threaded reply

            else:
                context.bot.send_message(chat_id=chat_id,
                                         text=formatted_caption,
                                         parse_mode=ParseMode.MARKDOWN_V2,
                                         reply_to_message_id=message_id)  # Threaded reply

def broadcast(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id not in admin_chat_ids:
        update.message.reply_text("You are not authorized to use this command.")
        return

    if context.args:
        message = ' '.join(context.args)
        for chat_id in chat_ids:
            try:
                context.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Failed to send message to {chat_id}: {e}")
        update.message.reply_text("Broadcast message sent to all subscribers.")
    else:
        update.message.reply_text("Usage: /broadcast <message>")

def subscribe(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in chat_ids:
        chat_ids.add(chat_id)
        save_chat_ids()
        update.message.reply_text("You have been subscribed to broadcasts.")
    else:
        update.message.reply_text("You are already subscribed.")

def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in chat_ids:
        chat_ids.add(chat_id)
        save_chat_ids()

def main() -> None:
    # Check if the TOKEN is defined
    if TOKEN is None:
        logger.error("Telegram bot token not found. Please set the TOKEN environment variable in your .env file.")
        return

    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register the /start command
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('subscribe', subscribe))  # Register the /subscribe command

    # Register the broadcast command
    dispatcher.add_handler(CommandHandler('broadcast', broadcast))

    # Register the handler for editing captions
    dispatcher.add_handler(MessageHandler(Filters.caption, edit_caption))

    # Register the message handler for saving chat IDs
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
