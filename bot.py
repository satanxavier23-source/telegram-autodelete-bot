from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

async def clean_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    links = [line.strip() for line in text.splitlines() if line.strip().startswith("http")]

    if not links:
        await update.message.reply_text("No links found ❌")
        return

    message = "FULL VIDEO 👀🌸\n\n" + "\n\n".join(
        [f"VIDEO {i+1} ⤵️\n{link}" for i, link in enumerate(links)]
    )

    await update.message.reply_text(message)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, clean_links))

app.run_polling()
