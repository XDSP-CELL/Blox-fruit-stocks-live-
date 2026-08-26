"""
Blox Fruits Stock Telegram Bot
--------------------------------
Kaam: /stock bhejte hi bot 2 buttons deta hai - "Normal Stock" aur
"Mirage Stock". Jo bhi dabayein, us category ka live stock bold +
fruit-emoji ke saath dikha deta hai (bina rarity/price ke).

Setup:
1. pip install -r requirements.txt
2. TELEGRAM_BOT_TOKEN environment variable set karein
3. Run: python stock_bot.py
"""

import os
import re
import logging

import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

STOCK_URL = "https://bloxfruitscode.com/blox-fruits-stock-live-right-now/"

OWNER_LINE = "Owner: @xdsp18 (fruit perms, gamepass, etc. ke liye contact karein)"

FRUIT_PATTERN = re.compile(
    r"([A-Z][A-Za-z\s]{1,20}?)\s+"
    r"(COMMON|UNCOMMON|RARE|LEGENDARY|MYTHICAL)\s+"
    r"Beli\s+([\d,]+)\s+Robux\s+([\d,]+)"
)

# Fruit naam (lowercase) -> emoji. Jo fruit list me nahi mile, unke liye
# default emoji use hoga.
FRUIT_EMOJIS = {
    "buddha": "🙏", "dark": "🌑", "light": "💡", "magma": "🌋",
    "ice": "❄️", "sand": "🏜️", "flame": "🔥", "smoke": "💨",
    "spring": "🌀", "blade": "🗡️", "spike": "📌", "eagle": "🦅",
    "quake": "🌍", "diamond": "💎", "rubber": "🎈", "ghost": "👻",
    "love": "💕", "spider": "🕷️", "gravity": "🪐", "phoenix": "🔥",
    "pain": "💢", "dough": "🍞", "portal": "🌀", "rumble": "⚡",
    "blizzard": "🌨️", "sound": "🔊", "dragon": "🐉", "kitsune": "🦊",
    "yeti": "🧊", "leopard": "🐆", "venom": "🐍", "shadow": "🌚",
    "mammoth": "🦣", "gas": "☠️", "creation": "🌱", "soul": "💀",
    "spirit": "👻", "control": "🧠", "falcon": "🦅", "chop": "🪓",
    "spin": "🌀", "rocket": "🚀", "t-rex": "🦖", "trex": "🦖",
    "barrier": "🛡️", "leopard fruit": "🐆",
}

DEFAULT_EMOJI = "🍈"


def emoji_for(fruit_name: str) -> str:
    return FRUIT_EMOJIS.get(fruit_name.strip().lower(), DEFAULT_EMOJI)


def scrape_stock():
    """
    Website se Normal aur Mirage stock nikalta hai.
    Return: dict {"normal": [(name, rarity, beli, robux), ...], "mirage": [...]}
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(STOCK_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)

    result = {"normal": [], "mirage": []}

    idx_normal = full_text.find("Normal Stock")
    idx_normal_hist = full_text.find("Recent Stock History", idx_normal)
    if idx_normal != -1 and idx_normal_hist != -1:
        normal_section = full_text[idx_normal:idx_normal_hist]
        result["normal"] = FRUIT_PATTERN.findall(normal_section)

    idx_mirage = full_text.find("Mirage Stock", idx_normal_hist if idx_normal_hist != -1 else 0)
    idx_mirage_hist = full_text.find("Recent Stock History", idx_mirage)
    if idx_mirage != -1 and idx_mirage_hist != -1:
        mirage_section = full_text[idx_mirage:idx_mirage_hist]
        result["mirage"] = FRUIT_PATTERN.findall(mirage_section)

    return result


def format_category(label: str, fruits: list) -> str:
    lines = [f"<b>{label}</b>", ""]
    if fruits:
        for name, _rarity, _beli, _robux in fruits:
            clean_name = name.strip()
            lines.append(f"{emoji_for(clean_name)} <b>{clean_name}</b>")
    else:
        lines.append("Data nahi mila")
    lines.append("")
    lines.append(OWNER_LINE)
    return "\n".join(lines)


async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🍈 Normal Stock", callback_data="normal"),
            InlineKeyboardButton("✨ Mirage Stock", callback_data="mirage"),
        ]
    ]
    await update.message.reply_text(
        "Konsa stock dekhna hai?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data  # "normal" ya "mirage"
    label = "Normal Stock" if category == "normal" else "Mirage Stock"

    try:
        stock = scrape_stock()
        text = format_category(label, stock.get(category, []))
    except Exception as e:
        logger.exception("Scraping failed")
        text = f"Stock fetch nahi ho paya, error: {e}"

    keyboard = [
        [
            InlineKeyboardButton("🍈 Normal Stock", callback_data="normal"),
            InlineKeyboardButton("✨ Mirage Stock", callback_data="mirage"),
        ]
    ]
    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! /stock bhejein current Blox Fruits stock dekhne ke liye."
    )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Bot start ho raha hai (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
