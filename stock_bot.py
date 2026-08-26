"""
Blox Fruits Stock Telegram Bot
--------------------------------
Kaam: /stock bhejte hi bot 2 buttons deta hai - "Normal Stock" aur
"Mirage Stock". Jo bhi dabayein, us category ka live stock ek clean,
Discord-jaisa card format me dikhata hai (emoji + bold naam + price).

Setup:
1. pip install -r requirements.txt
2. TELEGRAM_BOT_TOKEN environment variable set karein
3. Run: python stock_bot.py
"""

import os
import re
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

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

# Jis group me automatic stock-refresh notifications jaani hain.
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "-1002855405684")

# Kitni der me bot background me stock check karega (seconds). Har check
# me sirf ek website request hoti hai, jab tak stock badle na, group me
# kuch bhi nahi bheja jaata.
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "120"))

STOCK_URL = "https://bloxfruitscode.com/blox-fruits-stock-live-right-now/"

OWNER_LINE = "👑 Owner: @xdsp18 — fruit perms, gamepass, etc. ke liye contact karein"

FRUIT_PATTERN = re.compile(
    r"([A-Z][A-Za-z\s]{1,20}?)\s+"
    r"(COMMON|UNCOMMON|RARE|LEGENDARY|MYTHICAL)\s+"
    r"Beli\s+([\d,]+)\s+Robux\s+([\d,]+)"
)

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
}

DEFAULT_EMOJI = "🍈"


def emoji_for(fruit_name: str) -> str:
    return FRUIT_EMOJIS.get(fruit_name.strip().lower(), DEFAULT_EMOJI)


def scrape_stock():
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
    header_emoji = "🍈" if label == "Normal Stock" else "✨"

    lines = [f"{header_emoji} <b>BLOX FRUITS — {label.upper()}</b>", ""]

    if fruits:
        for name, _rarity, beli, robux in fruits:
            clean_name = name.strip()
            lines.append(
                f"{emoji_for(clean_name)} <b>{clean_name}</b>"
                f"  —  💰 {beli} Beli  |  🎮 {robux} Robux"
            )
    else:
        lines.append("Data nahi mila")

    lines.append("")
    now_str = datetime.now(timezone.utc).strftime("%d %b, %I:%M %p UTC")
    lines.append(f"<i>Powered by GAMERBOT • {now_str}</i>")
    lines.append("")
    lines.append(OWNER_LINE)
    return "\n".join(lines)


def format_full_stock(stock: dict, refreshed: bool = False) -> str:
    lines = []
    if refreshed:
        lines.append("🔔 <b>STOCK REFRESHED!</b>")
        lines.append("")

    for key, title, emoji in (("normal", "NORMAL STOCK", "🍈"), ("mirage", "MIRAGE STOCK", "✨")):
        fruits = stock.get(key, [])
        lines.append(f"{emoji} <b>{title}</b>")
        if fruits:
            for name, _rarity, beli, robux in fruits:
                clean_name = name.strip()
                lines.append(
                    f"{emoji_for(clean_name)} <b>{clean_name}</b>"
                    f"  —  💰 {beli} Beli  |  🎮 {robux} Robux"
                )
        else:
            lines.append("Data nahi mila")
        lines.append("")

    now_str = datetime.now(timezone.utc).strftime("%d %b, %I:%M %p UTC")
    lines.append(f"<i>Powered by GAMERBOT • {now_str}</i>")
    lines.append("")
    lines.append(OWNER_LINE)
    return "\n".join(lines)


def stock_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🍈 Normal Stock", callback_data="normal"),
                InlineKeyboardButton("✨ Mirage Stock", callback_data="mirage"),
            ]
        ]
    )


async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍇 <b>Blox Fruits Stock</b>\nKonsa dekhna hai?",
        parse_mode="HTML",
        reply_markup=stock_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    label = "Normal Stock" if category == "normal" else "Mirage Stock"

    try:
        stock = scrape_stock()
        text = format_category(label, stock.get(category, []))
    except Exception as e:
        logger.exception("Scraping failed")
        text = f"Stock fetch nahi ho paya, error: {e}"

    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=stock_keyboard()
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! /stock bhejein current Blox Fruits stock dekhne ke liye."
    )


class _HealthHandler(BaseHTTPRequestHandler):
    """UptimeRobot (ya koi bhi pinger) jab is URL ko hit karega, bot
    zinda dikhega aur Render use sleep nahi karega."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        pass  # server logs ko chup rakhta hai, taaki asli logs saaf dikhein


def run_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    logger.info(f"Health server chal raha hai port {port} par")
    server.serve_forever()


def stock_signature(stock: dict):
    """Sirf fruit names se ek chhota 'fingerprint' banata hai taaki
    naya scrape purane se compare kiya ja sake."""
    return (
        tuple(sorted(name.strip() for name, *_ in stock.get("normal", []))),
        tuple(sorted(name.strip() for name, *_ in stock.get("mirage", []))),
    )


async def check_stock_job(context: ContextTypes.DEFAULT_TYPE):
    """Har CHECK_INTERVAL_SECONDS me chalta hai. Sirf tabhi group me
    message bhejta hai jab stock pichli baar se badla ho."""
    bot_data = context.application.bot_data

    try:
        stock = scrape_stock()
    except Exception:
        logger.exception("Background stock check fail hua")
        return

    new_sig = stock_signature(stock)
    old_sig = bot_data.get("last_stock_signature")

    if old_sig is None:
        # Pehli baar chal raha hai -- baseline set karo, notify mat karo
        bot_data["last_stock_signature"] = new_sig
        logger.info("Baseline stock set ho gaya, ab se changes track honge")
        return

    if new_sig != old_sig:
        bot_data["last_stock_signature"] = new_sig
        text = format_full_stock(stock, refreshed=True)
        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID, text=text, parse_mode="HTML"
            )
            logger.info("Stock change detect hua, group me notify kar diya")
        except Exception:
            logger.exception("Group me message bhejna fail hua")


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stock", stock_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.job_queue.run_repeating(
        check_stock_job, interval=CHECK_INTERVAL_SECONDS, first=10
    )
    logger.info("Bot start ho raha hai (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
