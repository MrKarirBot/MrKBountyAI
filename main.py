import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🛡️ Welcome to MrKBountyAI!

AI-powered assistant for ethical hackers, bug bounty hunters, and cybersecurity learners.

Menu:
/learn - Learn Bug Bounty
/owasp - OWASP Top 10
/checklist - Security Checklist
/report - Bug Report Template
/help - Help

⚠️ For educational purposes and authorized security testing only.
"""
    await update.message.reply_text(message)


async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Learn Bug Bounty:\n\n1. HTTP & HTTPS\n2. DNS\n3. OWASP Top 10\n4. Burp Suite\n5. Responsible Disclosure"
    )


async def owasp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ OWASP Top 10:\n\n1. Broken Access Control\n2. Cryptographic Failures\n3. Injection\n4. Insecure Design\n5. Security Misconfiguration\n6. Vulnerable Components\n7. Authentication Failures\n8. Software & Data Integrity Failures\n9. Logging & Monitoring Failures\n10. SSRF"
    )


async def checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Security Checklist:\n\n1. Read program scope\n2. Test only authorized targets\n3. Check login/logout\n4. Check access control\n5. Check file upload\n6. Check API endpoints\n7. Document evidence\n8. Report responsibly"
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Bug Report Template:\n\nTitle:\nSummary:\nTarget:\nSteps to Reproduce:\nImpact:\nEvidence:\nRecommendation:"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Commands:\n/start\n/learn\n/owasp\n/checklist\n/report\n/help"
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Set it in environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("owasp", owasp))
    app.add_handler(CommandHandler("checklist", checklist))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("help", help_command))

    print("MrKBountyAI is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
