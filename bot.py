import telebot
import re
import threading
import time

BOT_TOKEN = "YOUR_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def extract_links(text):
    return re.findall(r'https?://\S+', text)

def auto_send(user_id, chat_id):
    time.sleep(10)

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if len(data["links"]) == 0:
        return

    new_links = "\n\nFULL VIDEO 👀🌸\n\n"

    for i, link in enumerate(data["links"]):
        new_links += f"VIDEO {i+1} ⤵️\n{link}\n\n"

    final_caption = data["text"] + new_links

    bot.send_photo(
        chat_id,
        data["photo"],
        caption=final_caption
    )

    del user_data[user_id]

@bot.message_handler(content_types=['photo'])
def photo_handler(message):

    user_id = message.from_user.id

    user_data[user_id] = {
        "photo": message.photo[-1].file_id,
        "text": message.caption if message.caption else "",
        "links": []
    }

    bot.reply_to(message, "Send links now 🔗")

    threading.Thread(
        target=auto_send,
        args=(user_id, message.chat.id)
    ).start()

@bot.message_handler(content_types=['text'])
def text_handler(message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    links = extract_links(message.text)

    if links:
        user_data[user_id]["links"].extend(links)

print("Bot running...")
bot.infinity_polling()
