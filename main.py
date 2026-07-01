import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from google import genai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)


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
            InlineKeyboardButton("🤖 AI Mentor", callback_data="ai_mentor"),
            InlineKeyboardButton("🛠 Tools", callback_data="tools"),
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Welcome to MrKBountyAI!\n\n"
        "AI assistant for ethical hackers, bug bounty hunters, and cybersecurity learners.\n\n"
        "Pilih menu di bawah ini:",
        reply_markup=main_menu(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    responses = {
        "learn": (
            "📚 Learn Bug Bounty\n\n"
            "1. HTTP & HTTPS\n"
            "2. DNS & Subdomain\n"
            "3. OWASP Top 10\n"
            "4. Burp Suite dasar\n"
            "5. Responsible Disclosure"
        ),
        "owasp": (
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
        ),
        "checklist": (
            "✅ Security Checklist\n\n"
            "1. Baca scope program\n"
            "2. Uji hanya target yang diizinkan\n"
            "3. Cek login/logout\n"
            "4. Cek access control\n"
            "5. Cek upload file\n"
            "6. Cek endpoint API\n"
            "7. Simpan bukti\n"
            "8. Laporkan dengan responsible disclosure"
        ),
        "report": (
            "📝 Bug Report Template\n\n"
            "Title:\n"
            "Summary:\n"
            "Target:\n"
            "Steps to Reproduce:\n"
            "Impact:\n"
            "Evidence:\n"
            "Recommendation:"
        ),
        "ai_mentor": (
            "🤖 AI Mentor aktif.\n\n"
            "Ketik pertanyaan kamu langsung di chat.\n\n"
            "Contoh:\n"
            "Apa itu IDOR?\n"
            "Jelaskan SSRF dengan analogi sederhana.\n"
            "Buat checklist XSS untuk pemula."
        ),
        "tools": (
            "🛠 Tools Reference\n\n"
            "• Burp Suite\n"
            "• OWASP ZAP\n"
            "• Nmap\n"
            "• Wireshark\n"
            "• Postman\n\n"
            "Gunakan hanya pada target yang punya izin resmi."
        ),
        "about": (
            "ℹ️ About MrKBountyAI\n\n"
            "Bot pembelajaran dan produktivitas untuk ethical hacking, "
            "bug bounty, dan cybersecurity.\n\n"
            "⚠️ Untuk edukasi dan authorized testing only."
        ),
        "help": (
            "❓ Help\n\n"
            "Gunakan /start untuk membuka menu.\n"
            "Ketik pertanyaan apa pun untuk AI Mentor."
        ),
    }

    await query.edit_message_text(
        text=responses.get(data, "Menu tidak ditemukan."),
        reply_markup=main_menu(),
    )


async def ai_mentor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if not GEMINI_API_KEY:
        await update.message.reply_text(
            "⚠️ GEMINI_API_KEY belum diatur di Railway Variables."
        )
        return

    prompt = f"""
Kamu adalah MrKBountyAI, mentor cybersecurity dan bug bounty yang legal, aman, dan edukatif.

Aturan:
- Jawab dalam bahasa Indonesia.
- Fokus pada pembelajaran, defensive security, authorized testing, dan responsible disclosure.
- Jangan memberi instruksi eksploitasi ilegal, pencurian data, bypass akses, malware, phishing, atau penyalahgunaan.
- Jika pertanyaan berisiko, arahkan ke konsep aman, mitigasi, lab legal, atau checklist etis.
- Jawaban harus ringkas, jelas, dan praktis.

Pertanyaan user:
{user_text}
"""

    try:
        response = ai_client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )

        answer = response.text or "Maaf, AI tidak memberikan jawaban."
        await update.message.reply_text(answer[:4000])

    except Exception as error:
        await update.message.reply_text(
            f"⚠️ AI error:\n{error}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "Gunakan /start untuk membuka menu.\n"
        "Ketik pertanyaan langsung untuk memakai AI Mentor."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with AI Mentor...")
    app.run_polling()


if __name__ == "__main__":
    main()
