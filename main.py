print("MAIN VERSION 999 WHATSAPP WEBHOOK ACTIVE")
print("MAIN VERSION TELEGRAM + WHATSAPP WEBHOOK")

import os
import asyncio
import threading
import requests
from dotenv import load_dotenv
from flask import Flask, request

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

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mrkbountyai_verify")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")

AI_MODEL = "llama-3.1-8b-instant"
MAX_TELEGRAM_MESSAGE = 3900
MAX_WHATSAPP_MESSAGE = 3900

ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
flask_app = Flask(__name__)


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
        "autonomous": "🤖 Autonomous Security Agent aktif.",
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
            "/scan https://example.com - Analisis header keamanan URL"
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

    history = get_history(user_id, limit=10)

    memory_messages = []
    for item in history:
        role = item["role"]
        message = item["message"]

        if role in ["user", "assistant"] and message:
            memory_messages.append({"role": role, "content": message})

    return [
        {"role": "system", "content": autonomous_prompt},
        *memory_messages,
        {"role": "user", "content": user_text},
    ]


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


def generate_ai_answer_sync(user_id: int, user_text: str) -> str:
    if not ai_client:
        return "⚠️ GROQ_API_KEY belum diatur di Railway Variables."

    try:
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=build_ai_messages(user_id, user_text),
            temperature=0.4,
            max_tokens=1200,
        )

        answer = response.choices[0].message.content or "Maaf, AI tidak memberi jawaban."

        save_message(user_id, "user", user_text)
        save_message(user_id, "assistant", answer)

        return answer

    except Exception as error:
        return f"⚠️ AI error.\n\nDetail: {error}"


async def ai_mentor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    if not ai_client:
        await update.message.reply_text("⚠️ GROQ_API_KEY belum diatur di Railway Variables.")
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
            "/scan https://example.com"
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


def send_whatsapp_message(to: str, text: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("WHATSAPP_TOKEN atau PHONE_NUMBER_ID belum diatur.")
        return

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:MAX_WHATSAPP_MESSAGE]},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code >= 400:
        print(f"WhatsApp send error: {response.status_code} {response.text}")


@flask_app.route("/", methods=["GET"])
def home():
    return "MrKBountyAI Telegram + WhatsApp Webhook is running.", 200


@flask_app.route("/webhook", methods=["GET"])
def verify_whatsapp_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WhatsApp webhook verified.")
        return challenge, 200

    return "Verification failed", 403


@flask_app.route("/webhook", methods=["POST"])
def receive_whatsapp_message():
    data = request.get_json(silent=True) or {}

    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return "OK", 200

        message = messages[0]
        sender = message.get("from")

        if not sender:
            return "OK", 200

        if message.get("type") != "text":
            send_whatsapp_message(
                sender,
                "⚠️ Saat ini saya hanya bisa membaca pesan teks."
            )
            return "OK", 200

        user_text = message.get("text", {}).get("body", "").strip()

        if not user_text:
            send_whatsapp_message(sender, "Kirim pesan teks ya.")
            return "OK", 200

        user_id = int(sender)
        answer = generate_ai_answer_sync(user_id, user_text)
        send_whatsapp_message(sender, answer)

    except Exception as error:
        print(f"WhatsApp webhook error: {error}")

    return "OK", 200


def run_flask_server():
    port = int(os.getenv("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in Railway Variables.")

    init_database()
    init_vector_database()
    ingest_knowledge_base()

    threading.Thread(target=run_flask_server, daemon=True).start()

    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("scan", scan_command))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_mentor))

    print("MrKBountyAI is running with Telegram + WhatsApp Webhook...")
    telegram_app.run_polling()


if __name__ == "__main__":
    main()
