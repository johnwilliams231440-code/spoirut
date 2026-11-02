import os
import json
import html
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CONTACT_TEXT = os.environ.get("CONTACT_TEXT", "Contact us: @your_username")


def load_bonuses():
    path = os.path.join(os.path.dirname(__file__), "bonuses.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Could not load bonuses.json: %s", e)
        return []


def main_menu():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎁 See Bonuses", callback_data="bonuses")],
            [
                InlineKeyboardButton("❓ Help", callback_data="help"),
                InlineKeyboardButton("📞 Contact", callback_data="contact"),
            ],
        ]
    )


def bonuses_content():
    bonuses = load_bonuses()
    if not bonuses:
        return "No bonuses available right now. Please check back soon.", None

    lines = ["<b>🎁 Current Bonuses</b>\n"]
    buttons = []
    for i, b in enumerate(bonuses, start=1):
        title = html.escape(b.get("title", "Bonus"))
        desc = html.escape(b.get("description", ""))
        lines.append(f"<b>{i}. {title}</b>\n{desc}\n")
        link = b.get("link")
        if link:
            buttons.append([InlineKeyboardButton(f"Claim: {b.get('title', 'Bonus')}", url=link)])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


HELP_TEXT = (
    "<b>How to use Bonus Specialist</b>\n\n"
    "/start - Open the main menu\n"
    "/bonuses - See current bonuses\n"
    "/help - Show this help\n"
    "/contact - Get in touch"
)

WELCOME_TEXT = (
    "👋 Welcome to <b>Bonus Specialist</b>!\n\n"
    "I help you find the best bonuses and offers. "
    "Tap a button below to get started."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu()
    )


async def bonuses_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, markup = bonuses_content()
    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CONTACT_TEXT)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "bonuses":
        text, markup = bonuses_content()
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True
        )
    elif data == "help":
        back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
        await query.edit_message_text(HELP_TEXT, parse_mode="HTML", reply_markup=back)
    elif data == "contact":
        back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu")]])
        await query.edit_message_text(CONTACT_TEXT, reply_markup=back)
    elif data == "menu":
        await query.edit_message_text(
            WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu()
        )


async def post_init(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Start the bot"),
            BotCommand("bonuses", "See current bonuses"),
            BotCommand("help", "How to use the bot"),
            BotCommand("contact", "Get in touch"),
        ]
    )


# Tiny web server so Render sees an open port (needed for Web Service type)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bonuses", bonuses_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("contact", contact_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
