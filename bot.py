import telebot
import re

BOT_TOKEN = "YOUR_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

# 🔗 Extract links
def extract_links(text):
    return re.findall(r'https?://\S+', text)

# 📸 Photo വന്നാൽ
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.id

    user_data[user_id] = {
        "photo": message.photo[-1].file_id,
        "links": []
    }

    bot.reply_to(message, "Send links 🔗")

# 🔗 Links വന്നാൽ
@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id

    if user_id not in user_data:
        return

    links = extract_links(message.text)

    if links:
        user_data[user_id]["links"].extend(links)

        data = user_data[user_id]

        # 🔥 Stylish format
        new_links = "FULL VIDEO 👀🌸\n\n"

        for i, link in enumerate(data["links"], start=1):
            new_links += f"VIDEO {i} ⤵️\n{link}\n\n"

        # 📸 Send photo (no caption)
        bot.send_photo(
            message.chat.id,
            data["photo"]
        )

        # 📩 Send links message
        bot.send_message(
            message.chat.id,
            new_links
        )

        # 🧹 Clear data
        del user_data[user_id]

print("Bot running...")
bot.infinity_polling()
