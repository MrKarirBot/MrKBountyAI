import os
import asyncio
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

from app.database.database import init_database
from app.database.memory import save_message, get_history
from app.services.agent import detect_intent, build_agent_prompt
from app.knowledge.kb import search_knowledge_base

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

AI_MODEL = "llama-3.1-8b-instant"
MAX_TELEGRAM_MESSAGE = 3900

ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


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
            InlineKeyboardButton("📚 Knowledge", callback_data="knowledge"),
        ],
        [
            InlineKeyboardButton("🧠 Memory", callback_data="memory"),
            InlineKeyboardButton("🧭 Agent", callback_data="agent"),
        ],
        [
            InlineKeyboardButton("🛠 Tools", callback_data="tools"),
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Welcome to MrKBountyAI!\n\n"
        "AI Agent for ethical hackers, bug bounty hunters, and cybersecurity learners.\n\n"
        "Pilih menu di bawah ini:",
        reply_markup=main_menu(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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
            "Ketik pertanyaan langsung di chat.\n\n"
            "Contoh:\n"
            "• Apa itu IDOR?\n"
            "• Jelaskan SSRF dengan analogi sederhana.\n"
            "• Buat checklist XSS untuk pemula."
        ),
        "knowledge": (
            "📚 Knowledge Base aktif.\n\n"
            "Bot akan mencari jawaban dari file di folder:\n"
            "`app/knowledge/*.md`\n\n"
            "Contoh:\n"
            "• Jelaskan Broken Access Control\n"
            "• Apa mitigasi SSRF?\n"
            "• Apa itu XSS menurut OWASP?"
        ),
        "memory": (
            "🧠 Memory AI aktif.\n\n"
            "Percakapan disimpan ke PostgreSQL agar bot bisa mengingat konteks.\n\n"
            "Tes:\n"
            "1. Ketik: Nama saya Kusnadi.\n"
            "2. Ketik: Siapa nama saya?"
        ),
        "agent": (
            "🧭 AI Agent aktif.\n\n"
            "Bot bisa mendeteksi maksud pertanyaan otomatis.\n\n"
            "Contoh:\n"
            "• Apa itu XSS?\n"
            "• Buat checklist pengujian IDOR.\n"
            "• Buat bug report untuk Broken Access Control.\n"
            "• Jelaskan OWASP Top 10."
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
        "help": (
            "❓ Help\n\n"
            "/start - Menu utama\n"
            "/help - Bantuan\n\n"
            "Ketik pertanyaan langsung untuk memakai AI Agent."
        ),
    }

    await query.edit_message_text(
        text=responses.get(query.data, "Menu tidak ditemukan."),
        reply_markup=main_menu(),
    )


def build_knowledge_context(user_text: str) -> str:
    docs = search_knowledge_base(user_text, max_results=2)

    if not docs:
        return "Tidak ada konteks khusus yang ditemukan di Knowledge Base."

    context_blocks = []

    for doc in docs:
        source = doc.get("source", "unknown")
        content = doc.get("content", "")

        context_blocks.append(
            f"Sumber: {source}\n\n{content}"
        )

    return "\n\n---\n\n".join(context_blocks)


def build_ai_messages(user_id: int, user_text: str):
    intent = detect_intent(user_text)
    agent_prompt = build_agent_prompt(intent, user_text)
    knowledge_context = build_knowledge_context(user_text)

    system_message = {
        "role": "system",
        "content": (
            f"{agent_prompt}\n\n"
            "Gunakan Knowledge Base berikut sebagai referensi utama jika relevan.\n"
            "Jika Knowledge Base tidak cukup menjawab, gunakan pengetahuan cybersecurity umum yang benar.\n\n"
            "================ KNOWLEDGE BASE ================\n"
            f"{knowledge_context}\n"
            "================================================"
        ),
    }

    history = get_history(user_id, limit=10)

    memory_messages = []
    for item in history:
        role = item["role"]
        message = item["message"]

        if role in ["user", "assistant"] and message:
            memory_messages.append(
                {
                    "role": role,
                    "content": message,
                }
            )

    current_message = {
        "role": "user",
        "content": user_text,
    }

    return [system_message] + memory_messages + [current_message]


async def generate_ai_answer(user_id: int, user_text: str) -> str:
    last_error = None

    for attempt in range(3):
        try:
            messages = build_ai_messages(user_id, user_text)

            response = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=900,
            )

            return response.choices[0].message.content or "Maaf, AI tidak memberi jawaban."

        except Exception as error:
            last_error = str(error)
            await asyncio.sleep(1 + attempt)

    return (
        "⚠️ AI Agent sedang sibuk atau terkena limit sementara.\n\n"
        f"Detail singkat: {last_error[:300]}"
    )


async def ai_mentor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    if not ai_client:
        await update.message.reply_text(
            "⚠️ GROQ_API_KEY belum diatur di Railway Variables."
        )
        return

    thinking_message = await update.message.reply_text("🤖 Agent sedang menganalisis Knowledge Base...")

    try:
        answer = await generate_ai_answer(user_id, user_text)

        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", answer)

        if len(answer) > MAX_TELEGRAM_MESSAGE:
            answer = answer[:MAX_TELEGRAM_MESSAGE] + "\n\n...jawaban dipotong karena terlalu panjang."

        await thinking_message.edit_text(answer)

    except Exception as error:
        await thinking_message.edit_text(
            "⚠️ AI Agent error.\n\n"
            f"Detail:\n{error}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "/start - Menu utama\n"
        "/help - Bantuan\n\n"
        "Ketik pertanyaan langsung untuk memakai AI Agent + Knowledge Base."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in Railway Variables.")

    init_database()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with AI Agent, Memory, and Knowledge Base...")
    app.run_polling()


if __name__ == "__main__":
    main()
