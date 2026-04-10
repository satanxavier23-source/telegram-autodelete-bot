import telebot
import re

BOT_TOKEN = "YOUR_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def extract_links(text):
    return re.findall(r'https?://\S+', text)

# 📸 Photo handler (caption ignore ❌)
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.id

    user_data[user_id] = {
        "photo": message.photo[-1].file_id,
        "links": []
    }

    bot.reply_to(message, "Now send links 🔗")

# 🔗 Link handler
@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id

    if user_id not in user_data:
        return

    links = extract_links(message.text)

    if links:
        user_data[user_id]["links"].extend(links)
        send_result(message.chat.id, user_id)

# 🚀 Send result
def send_result(chat_id, user_id):
    data = user_data.get(user_id)

    if not data or not data["links"]:
        return

    new_links = "FULL VIDEO 👀🌸\n\n"

    for i, link in enumerate(data["links"], start=1):
        new_links += f"VIDEO {i} ⤵️\n{link}\n\n"

    # 📸 Photo
    bot.send_photo(chat_id, data["photo"])

    # 🔗 Links
    bot.send_message(chat_id, new_links)

    user_data.pop(user_id, None)

print("Bot running...")
bot.infinity_polling()
