from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📚 Learn", callback_data="learn")],
        [InlineKeyboardButton("🛡 OWASP Top 10", callback_data="owasp")],
        [InlineKeyboardButton("✅ Checklist", callback_data="checklist")],
        [InlineKeyboardButton("📝 Report", callback_data="report")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]

    return InlineKeyboardMarkup(keyboard)
