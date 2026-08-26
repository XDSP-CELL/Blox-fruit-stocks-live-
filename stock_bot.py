"""
Blox Fruits Stock Telegram Bot
--------------------------------
Kaam: Telegram me /stock command bhejte hi yeh bot bloxfruitscode.com se
live Normal + Mirage stock scrape karke aapko turant reply kar deta hai.

Setup:
1. pip install -r requirements.txt
2. TELEGRAM_BOT_TOKEN environment variable set karein (.env file ya Render
   Environment tab me -- kabhi bhi code me hardcode na karein)
3. Run: python stock_bot.py
4. Telegram me apne bot ko /stock bhejein
"""

import os
import re
import logging

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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

# Pattern jo "FruitName RARITY Beli 1,200,000 Robux 1,650" jaisi lines pakadta hai
FRUIT_PATTERN = re.compile(
    r"([A-Z][A-Za-z\s]{1,20}?)\s+"
    r"(COMMON|UNCOMMON|RARE|LEGENDARY|MYTHICAL)\s+"
    r"Beli\s+([\d,]+)\s+Robux\s+([\d,]+)"
)


def scrape_stock():
    """
    Website se Normal aur Mirage stock nikalta hai.
    Return: dict {"normal": [...], "mirage": [...]}
    Agar site ka structure badal jaye to yahan selectors/regex adjust karne
    padenge -- niche 'agar scraping fail ho' waala note dekhein.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(STOCK_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)

    result = {"normal": [], "mirage": []}

    # Normal Stock section: "Normal Stock" heading se lekar uske "Recent Stock
    # History" tak (yeh current stock hai, history table nahi)
    idx_normal = full_text.find("Normal Stock")
    idx_normal_hist = full_text.find("Recent Stock History", idx_normal)
    if idx_normal != -1 and idx_normal_hist != -1:
        normal_section = full_text[idx_normal:idx_normal_hist]
        result["normal"] = FRUIT_PATTERN.findall(normal_section)

    # Mirage Stock section: pehli "Recent Stock History" ke baad wala
    # "Mirage Stock" heading se lekar uske apne "Recent Stock History" tak
    idx_mirage = full_text.find("Mirage Stock", idx_normal_hist if idx_normal_hist != -1 else 0)
    idx_mirage_hist = full_text.find("Recent Stock History", idx_mirage)
    if idx_mirage != -1 and idx_mirage_hist != -1:
        mirage_section = full_text[idx_mirage:idx_mirage_hist]
        result["mirage"] = FRUIT_PATTERN.findall(mirage_section)

    return result


def format_stock_message(stock: dict) -> str:
    lines = ["Blox Fruits Stock (Live)", ""]

    lines.append("Normal Stock:")
    if stock["normal"]:
        for name, rarity, beli, robux in stock["normal"]:
            lines.append(f"- {name.strip()} ({rarity}) | Beli {beli} | Robux {robux}")
    else:
        lines.append("- Data nahi mila")

    lines.append("")
    lines.append("Mirage Stock:")
    if stock["mirage"]:
        for name, rarity, beli, robux in stock["mirage"]:
            lines.append(f"- {name.strip()} ({rarity}) | Beli {beli} | Robux {robux}")
    else:
        lines.append("- Data nahi mila")

    lines.append("")
    lines.append(f"Source: {STOCK_URL}")
    return "\n".join(lines)


async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Stock check kar raha hoon...")
    try:
        stock = scrape_stock()
        message = format_stock_message(stock)
    except Exception as e:
        logger.exception("Scraping failed")
        message = f"Stock fetch nahi ho paya, error: {e}"
    await update.message.reply_text(message)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! /stock bhejein current Blox Fruits stock dekhne ke liye."
    )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stock", stock_command))
    logger.info("Bot start ho raha hai (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
