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

from app.agents.master_agent import detect_agent, build_master_prompt
from app.agents.mentor_agent import build_mentor_prompt
from app.agents.owasp_agent import build_owasp_prompt
from app.agents.report_agent import build_report_prompt
from app.agents.checklist_agent import build_checklist_prompt
from app.agents.memory_agent import build_memory_prompt

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
            InlineKeyboardButton("🤖 Mentor", callback_data="ai_mentor"),
            InlineKeyboardButton("🧠 Memory", callback_data="memory"),
        ],
        [
            InlineKeyboardButton("🧭 Multi-Agent", callback_data="agent"),
            InlineKeyboardButton("🔎 Vector RAG", callback_data="vector_rag"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Welcome to MrKBountyAI!\n\n"
        "Multi-Agent AI for ethical hackers, bug bounty hunters, and cybersecurity learners.\n\n"
        "Pilih menu di bawah ini:",
        reply_markup=main_menu(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    responses = {
        "learn": "📚 Learn Agent aktif.\n\nKetik pertanyaan seperti:\n• Apa itu XSS?\n• Jelaskan IDOR\n• Apa itu SSRF?",
        "owasp": "🛡 OWASP Agent aktif.\n\nContoh:\n• Jelaskan Broken Access Control\n• Apa mitigasi SSRF?\n• OWASP Injection itu apa?",
        "checklist": "✅ Checklist Agent aktif.\n\nContoh:\n• Buat checklist pengujian API\n• Buat checklist IDOR\n• Checklist XSS untuk pemula",
        "report": "📝 Report Agent aktif.\n\nContoh:\n• Buat bug report Broken Access Control\n• Buat template laporan XSS\n• Susun laporan bug bounty",
        "ai_mentor": "🤖 Mentor Agent aktif.\n\nKetik pertanyaan cybersecurity langsung di chat.",
        "memory": "🧠 Memory Agent aktif.\n\nContoh:\n• Nama saya Kusnadi\n• Siapa nama saya?\n\nMemory disimpan di PostgreSQL.",
        "agent": "🧭 Multi-Agent aktif.\n\nBot akan memilih agent otomatis:\n• Mentor Agent\n• OWASP Agent\n• Report Agent\n• Checklist Agent\n• Memory Agent",
        "vector_rag": "🔎 Vector RAG aktif.\n\nBot mencari konteks berdasarkan kemiripan makna dari Knowledge Base.",
        "help": "❓ Help\n\n/start - Menu utama\n/help - Bantuan\n\nKetik pertanyaan langsung untuk memakai Multi-Agent AI.",
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
            source = chunk["source"]
            content = chunk["content"]
            distance = chunk["distance"]

            context_blocks.append(
                f"Sumber: {source}\n"
                f"Relevansi distance: {distance}\n\n"
                f"{content}"
            )

        return "\n\n---\n\n".join(context_blocks)

    except Exception as error:
        return f"Knowledge Base vector search error: {error}"


def build_specialist_prompt(agent_name: str, user_text: str, knowledge_context: str) -> str:
    if agent_name == "owasp_agent":
        return build_owasp_prompt(user_text, knowledge_context)

    if agent_name == "report_agent":
        return build_report_prompt(user_text, knowledge_context)

    if agent_name == "checklist_agent":
        return build_checklist_prompt(user_text, knowledge_context)

    if agent_name == "memory_agent":
        return build_memory_prompt(user_text, knowledge_context)

    return build_mentor_prompt(user_text, knowledge_context)


def build_ai_messages(user_id: int, user_text: str):
    agent_name = detect_agent(user_text)
    knowledge_context = build_knowledge_context(user_text)

    master_prompt = build_master_prompt(agent_name, user_text, knowledge_context)
    specialist_prompt = build_specialist_prompt(agent_name, user_text, knowledge_context)

    system_message = {
        "role": "system",
        "content": (
            f"{master_prompt}\n\n"
            "================ SPECIALIST AGENT ================\n"
            f"{specialist_prompt}\n"
            "==================================================\n\n"
            "Gunakan Vector Knowledge Base sebagai referensi utama jika relevan. "
            "Jika konteks belum cukup, gunakan pengetahuan cybersecurity umum yang benar dan aman."
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
        "⚠️ Multi-Agent sedang sibuk atau terkena limit sementara.\n\n"
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
        "🤖 Multi-Agent sedang memilih specialist agent..."
    )

    try:
        answer = await generate_ai_answer(user_id, user_text)

        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", answer)

        if len(answer) > MAX_TELEGRAM_MESSAGE:
            answer = answer[:MAX_TELEGRAM_MESSAGE] + "\n\n...jawaban dipotong karena terlalu panjang."

        await thinking_message.edit_text(answer)

    except Exception as error:
        await thinking_message.edit_text(
            "⚠️ Multi-Agent error.\n\n"
            f"Detail:\n{error}"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Help\n\n"
        "/start - Menu utama\n"
        "/help - Bantuan\n\n"
        "Ketik pertanyaan langsung untuk memakai Multi-Agent AI."
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
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with Multi-Agent AI, Memory, and Vector RAG...")
    app.run_polling()


if __name__ == "__main__":
    main()
