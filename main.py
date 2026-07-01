import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📚 Learn", callback_data="learn"),
            InlineKeyboardButton("🛡 OWASP", callback_data="owasp"),
        ],
        [
            InlineKeyboardButton("✅ Checklist", callback_data="checklist"),
            InlineKeyboardButton("📝 Report", callback_data="report"),
        ],
        [
            InlineKeyboardButton("🛠 Tools", callback_data="tools"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🛡 Welcome to MrKBountyAI!\n\n"
        "AI-powered assistant for ethical hackers, bug bounty hunters, "
        "and cybersecurity learners.\n\n"
        "Pilih menu di bawah ini:"
    )

    await update.message.reply_text(
        message,
        reply_markup=main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "learn":
        text = (
            "📚 Learn Bug Bounty\n\n"
            "Materi awal:\n"
            "1. HTTP & HTTPS\n"
            "2. DNS & Subdomain\n"
            "3. OWASP Top 10\n"
            "4. Burp Suite dasar\n"
            "5. Responsible Disclosure\n\n"
            "Fokus utama: belajar legal, aman, dan sesuai scope."
        )

    elif data == "owasp":
        text = (
            "🛡 OWASP Top 10\n\n"
            "1. Broken Access Control\n"
            "2. Cryptographic Failures\n"
            "3. Injection\n"
            "4. Insecure Design\n"
            "5. Security Misconfiguration\n"
            "6. Vulnerable Components\n"
            "7. Authentication Failures\n"
            "8. Software & Data Integrity Failures\n"
            "9. Logging & Monitoring Failures\n"
            "10. SSRF"
        )

    elif data == "checklist":
        text = (
            "✅ Security Checklist\n\n"
            "1. Baca scope program\n"
            "2. Uji hanya target yang diizinkan\n"
            "3. Cek login/logout\n"
            "4. Cek access control\n"
            "5. Cek upload file\n"
            "6. Cek endpoint API\n"
            "7. Simpan bukti dengan rapi\n"
            "8. Laporkan secara bertanggung jawab"
        )

    elif data == "report":
        text = (
            "📝 Bug Report Template\n\n"
            "Title:\n"
            "Summary:\n"
            "Target:\n"
            "Steps to Reproduce:\n"
            "Impact:\n"
            "Evidence:\n"
            "Recommendation:"
        )

    elif data == "tools":
        text = (
            "🛠 Tools Reference\n\n"
            "Rekomendasi belajar:\n"
            "• Burp Suite\n"
            "• OWASP ZAP\n"
            "• Nmap\n"
            "• Wireshark\n"
            "• Postman\n\n"
            "Gunakan hanya pada target yang punya izin resmi."
        )

    elif data == "about":
        text = (
            "ℹ️ About MrKBountyAI\n\n"
            "MrKBountyAI adalah bot pembelajaran dan produktivitas "
            "untuk ethical hacking dan bug bounty.\n\n"
            "Tujuan:\n"
            "• Belajar cybersecurity\n"
            "• Membuat checklist\n"
            "• Menyusun laporan\n"
            "• Memahami OWASP\n\n"
            "⚠️ Untuk edukasi dan authorized testing only."
        )

    else:
        text = (
            "❓ Help\n\n"
            "Gunakan /start untuk membuka menu utama.\n\n"
            "Perintah tersedia:\n"
            "/start\n"
            "/help"
        )

    await query.edit_message_text(
        text=text,
        reply_markup=main_menu()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "Gunakan /start untuk membuka menu utama MrKBountyAI."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("MrKBountyAI is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
