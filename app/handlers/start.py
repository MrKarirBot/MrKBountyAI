from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main_menu import main_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Welcome to MrKBountyAI!\n\n"
        "Silakan pilih menu di bawah ini.",
        reply_markup=main_menu()
    )
