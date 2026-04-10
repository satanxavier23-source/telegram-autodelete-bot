import os
import re
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found")
    raise SystemExit(1)

bot = telebot.TeleBot(BOT_TOKEN)

def extract_links(text):
    if not text:
        return []
    return re.findall(r'https?://[^\s]+', text)

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(
        message,
        "Photo + text + links ഒറ്റ message ആയി അയക്കൂ.\nഞാൻ text remove ചെയ്ത് links arrange ചെയ്ത് photo-യോടൊപ്പം തിരിച്ച് അയക്കും ✅"
    )

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    try:
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""

        links = extract_links(caption)

        if not links:
            bot.reply_to(message, "Caption-ിൽ valid links ഇല്ല ❌")
            return

        result = "FULL VIDEO 👀🌸\n\n"
        for i, link in enumerate(links, start=1):
            result += f"VIDEO {i} ⤵️\n{link}\n\n"

        # photo + arranged links together
        bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_id,
            caption=result
        )

    except Exception as e:
        print("ERROR:", e)
        bot.reply_to(message, "Error വന്നു ❌")

print("Bot running...")
bot.infinity_polling(skip_pending=True, none_stop=True)
