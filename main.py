import os
import asyncio
from collections import defaultdict
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
from groq import Groq

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

AI_MODEL = "llama-3.1-8b-instant"
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Memory sementara per user
user_memory = defaultdict(list)
MAX_MEMORY = 8


def main_menu():
    keyboard = [
        [InlineKeyboardButton("📚 Learn", callback_data="learn"), InlineKeyboardButton("🛡 OWASP", callback_data="owasp")],
        [InlineKeyboardButton("✅ Checklist", callback_data="checklist"), InlineKeyboardButton("📝 Report", callback_data="report")],
        [InlineKeyboardButton("🤖 AI Mentor", callback_data="ai_mentor"), InlineKeyboardButton("🛠 Tools", callback_data="tools")],
        [InlineKeyboardButton("🧠 Memory", callback_data="memory"), InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
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

    responses = {
        "learn": "📚 Learn Bug Bounty\n\n1. HTTP & HTTPS\n2. DNS & Subdomain\n3. OWASP Top 10\n4. Burp Suite\n5. Responsible Disclosure",
        "owasp": "🛡 OWASP Top 10\n\n1. Broken Access Control\n2. Cryptographic Failures\n3. Injection\n4. Insecure Design\n5. Security Misconfiguration\n6. Vulnerable Components\n7. Authentication Failures\n8. Software & Data Integrity Failures\n9. Logging & Monitoring Failures\n10. SSRF",
        "checklist": "✅ Security Checklist\n\n1. Baca scope program\n2. Uji hanya target yang diizinkan\n3. Cek login/logout\n4. Cek access control\n5. Cek upload file\n6. Cek API endpoint\n7. Simpan bukti\n8. Laporkan dengan responsible disclosure",
        "report": "📝 Bug Report Template\n\nTitle:\nSummary:\nTarget:\nSteps to Reproduce:\nImpact:\nEvidence:\nRecommendation:",
        "ai_mentor": "🤖 AI Mentor aktif.\n\nKetik pertanyaan langsung di chat.\n\nContoh:\nApa itu IDOR?\nIngat nama saya Kusnadi.\nSiapa nama saya?",
        "tools": "🛠 Tools Reference\n\n• Burp Suite\n• OWASP ZAP\n• Nmap\n• Wireshark\n• Postman\n\nGunakan hanya pada target yang punya izin resmi.",
        "memory": "🧠 Memory AI aktif.\n\nBot akan mengingat beberapa percakapan terakhir selama service Railway masih berjalan.\n\nGunakan /clear_memory untuk menghapus memory.",
        "about": "ℹ️ About MrKBountyAI\n\nBot AI untuk belajar ethical hacking, bug bounty, OWASP, dan cybersecurity.\n\n⚠️ Edukasi dan authorized testing only.",
        "help": "❓ Help\n\n/start - Menu utama\n/clear_memory - Hapus memory AI\n\nKetik pertanyaan langsung untuk memakai AI Mentor.",
    }

    await query.edit_message_text(
        text=responses.get(query.data, "Menu tidak ditemukan."),
        reply_markup=main_menu(),
    )


def build_ai_messages(user_id: int, user_text: str):
    system_message = {
        "role": "system",
        "content": (
            "Kamu adalah MrKBountyAI, mentor cybersecurity dan bug bounty yang legal, aman, dan edukatif. "
            "Jawab dalam bahasa Indonesia. Fokus pada pembelajaran, defensive security, authorized testing, "
            "dan responsible disclosure. Jangan memberi instruksi eksploitasi ilegal, pencurian data, bypass akses, "
            "malware, phishing, atau penyalahgunaan. Jika pertanyaan berisiko, arahkan ke konsep aman, mitigasi, "
            "lab legal, atau checklist etis. Jawaban harus ringkas, praktis, dan mudah dipahami."
        ),
    }

    memory = user_memory[user_id][-MAX_MEMORY:]
    current_message = {"role": "user", "content": user_text}

    return [system_message] + memory + [current_message]


async def generate_ai_answer(user_id: int, user_text: str) -> str:
    last_error = None

    for attempt in range(3):
        try:
            response = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=build_ai_messages(user_id, user_text),
                temperature=0.4,
                max_tokens=900,
            )

            return response.choices[0].message.content or "Maaf, AI tidak memberi jawaban."

        except Exception as error:
            last_error = str(error)
            await asyncio.sleep(1 + attempt)

    return f"⚠️ AI Mentor sedang sibuk atau terkena limit sementara.\n\nDetail: {last_error[:300]}"


async def ai_mentor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    if not ai_client:
        await update.message.reply_text("⚠️ GROQ_API_KEY belum diatur di Railway Variables.")
        return

    thinking_message = await update.message.reply_text("🤖 Sedang berpikir...")

    try:
        answer = await generate_ai_answer(user_id, user_text)

        # Simpan percakapan ke memory
        user_memory[user_id].append({"role": "user", "content": user_text})
        user_memory[user_id].append({"role": "assistant", "content": answer})

        # Batasi memory agar bot tidak berat
        if len(user_memory[user_id]) > MAX_MEMORY:
            user_memory[user_id] = user_memory[user_id][-MAX_MEMORY:]

        if len(answer) > 3900:
            answer = answer[:3900] + "\n\n...jawaban dipotong karena terlalu panjang."

        await thinking_message.edit_text(answer)

    except Exception as error:
        await thinking_message.edit_text(f"⚠️ AI Mentor error:\n{error}")


async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_memory[user_id].clear()
    await update.message.reply_text("🧠 Memory percakapan kamu sudah dihapus.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "/start - Menu utama\n"
        "/clear_memory - Hapus memory AI\n\n"
        "Ketik pertanyaan langsung untuk memakai AI Mentor."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in Railway Variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear_memory", clear_memory))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with Memory AI...")
    app.run_polling()


if __name__ == "__main__":
    main()
