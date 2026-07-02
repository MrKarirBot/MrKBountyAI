print("MAIN VERSION 275 FIXED")
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
from app.knowledge.vector_store import (
    init_vector_database,
    ingest_knowledge_base,
    search_similar_chunks,
)
from app.agents.autonomous_agent import build_autonomous_prompt
from app.tools.url_scanner import analyze_url_security

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

AI_MODEL = "llama-3.1-8b-instant"
MAX_TELEGRAM_MESSAGE = 3900

ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🤖 Autonomous Agent", callback_data="autonomous")],
        [
            InlineKeyboardButton("🔍 URL Scan", callback_data="scan_info"),
            InlineKeyboardButton("🔎 Vector RAG", callback_data="vector_rag"),
        ],
        [
            InlineKeyboardButton("📚 Learn", callback_data="learn"),
            InlineKeyboardButton("🛡 OWASP", callback_data="owasp"),
        ],
        [
            InlineKeyboardButton("✅ Checklist", callback_data="checklist"),
            InlineKeyboardButton("📝 Report", callback_data="report"),
        ],
        [
            InlineKeyboardButton("🧠 Memory", callback_data="memory"),
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Welcome to MrKBountyAI!\n\n"
        "Autonomous Security Agent untuk ethical hacking, bug bounty, dan cybersecurity learning.\n\n"
        "Pilih menu di bawah ini:",
        reply_markup=main_menu(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    responses = {
        "autonomous": (
            "🤖 Autonomous Security Agent aktif.\n\n"
            "Contoh:\n"
            "• Analisis kerentanan IDOR\n"
            "• Buat checklist dan report untuk XSS\n"
            "• Jelaskan SSRF dari sisi OWASP dan mitigasi"
        ),
        "scan_info": (
            "🔍 URL Security Scanner aktif.\n\n"
            "Gunakan format:\n"
            "/scan https://example.com\n\n"
            "Gunakan hanya pada target yang kamu punya izin."
        ),
        "learn": "📚 Learn Agent aktif.\n\nContoh: Apa itu XSS?",
        "owasp": "🛡 OWASP Agent aktif.\n\nContoh: Jelaskan Broken Access Control.",
        "checklist": "✅ Checklist Agent aktif.\n\nContoh: Buat checklist pengujian API.",
        "report": "📝 Report Agent aktif.\n\nContoh: Buat bug report Broken Access Control.",
        "memory": "🧠 Memory aktif.\n\nPercakapan disimpan di PostgreSQL.",
        "vector_rag": "🔎 Vector RAG aktif.\n\nBot mencari konteks berdasarkan kemiripan makna.",
        "help": (
            "❓ Help\n\n"
            "/start - Menu utama\n"
            "/scan https://example.com - Analisis header keamanan URL\n\n"
            "Ketik pertanyaan langsung untuk memakai Autonomous Security Agent."
        ),
    }

    await query.edit_message_text(
        text=responses.get(query.data, "Menu tidak ditemukan."),
        reply_markup=main_menu(),
    )


def build_knowledge_context(user_text: str) -> str:
    try:
        chunks = search_similar_chunks(user_text, limit=3)

        if not chunks:
            return "Tidak ada konteks relevan di Knowledge Base."

        context_blocks = []

        for chunk in chunks:
            context_blocks.append(
                f"Sumber: {chunk['source']}\n"
                f"Relevansi distance: {chunk['distance']}\n\n"
                f"{chunk['content']}"
            )

        return "\n\n---\n\n".join(context_blocks)

    except Exception as error:
        return f"Knowledge Base search error: {error}"


def build_ai_messages(user_id: int, user_text: str):
    knowledge_context = build_knowledge_context(user_text)
    autonomous_prompt = build_autonomous_prompt(user_text, knowledge_context)

    system_message = {
        "role": "system",
        "content": autonomous_prompt,
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
            response = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=build_ai_messages(user_id, user_text),
                temperature=0.4,
                max_tokens=1200,
            )

            return response.choices[0].message.content or "Maaf, AI tidak memberi jawaban."

        except Exception as error:
            last_error = str(error)
            await asyncio.sleep(1 + attempt)

    return (
        "⚠️ Autonomous Agent sedang sibuk atau terkena limit sementara.\n\n"
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

    thinking_message = await update.message.reply_text(
        "🤖 Autonomous Security Agent sedang menganalisis..."
    )

    try:
        answer = await generate_ai_answer(user_id, user_text)

        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", answer)

        if len(answer) > MAX_TELEGRAM_MESSAGE:
            answer = answer[:MAX_TELEGRAM_MESSAGE] + "\n\n...jawaban dipotong."

        await thinking_message.edit_text(answer)

    except Exception as error:
        await thinking_message.edit_text(
            "⚠️ Autonomous Agent error.\n\n"
            f"Detail:\n{error}"
        )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Gunakan format:\n"
            "/scan https://example.com\n\n"
            "Pastikan target berada dalam scope dan kamu punya izin."
        )
        return

    url = context.args[0]

    loading = await update.message.reply_text(
        "🔍 Security Copilot sedang menganalisis URL..."
    )

    try:
        result = analyze_url_security(url)

        if len(result) > MAX_TELEGRAM_MESSAGE:
            result = result[:MAX_TELEGRAM_MESSAGE] + "\n\n...hasil dipotong."

        await loading.edit_text(result)

    except Exception as error:
        await loading.edit_text(
            "❌ Scan gagal.\n\n"
            f"{error}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "/start - Menu utama\n"
        "/scan https://example.com - Analisis header keamanan URL\n\n"
        "Ketik pertanyaan langsung untuk memakai Autonomous Security Agent."
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in Railway Variables.")

    init_database()
    init_vector_database()
    ingest_knowledge_base()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with Security Copilot URL Scanner...")
    app.run_polling()


if __name__ == "__main__":
    main()
