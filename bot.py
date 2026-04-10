import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Token ഇല്ല ❌")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# 👉 നിന്റെ ID ഇവിടെ set ചെയ്തിട്ടുണ്ട്
ADMIN_ID = 6630347046

replace_photo = None
replace_mode = False
waiting_photo = False


def extract_links(text):
    if not text:
        return []
    return re.findall(r'https?://\S+', text)


def keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Set Photo")
    markup.row("ON", "OFF")
    markup.row("Status")
    return markup


@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Bot ready ✅", reply_markup=keyboard())


@bot.message_handler(func=lambda m: m.text == "Set Photo")
def set_photo(msg):
    global waiting_photo

    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "Admin only ❌")
        return

    waiting_photo = True
    bot.reply_to(msg, "Photo അയക്കൂ 📸")


@bot.message_handler(func=lambda m: m.text == "ON")
def turn_on(msg):
    global replace_mode

    if msg.from_user.id != ADMIN_ID:
        return

    if not replace_photo:
        bot.reply_to(msg, "Photo set ചെയ്തിട്ടില്ല ❌")
        return

    replace_mode = True
    bot.reply_to(msg, "ON ആയി ✅")


@bot.message_handler(func=lambda m: m.text == "OFF")
def turn_off(msg):
    global replace_mode

    if msg.from_user.id != ADMIN_ID:
        return

    replace_mode = False
    bot.reply_to(msg, "OFF ആയി ❌")


@bot.message_handler(func=lambda m: m.text == "Status")
def status(msg):
    mode = "ON" if replace_mode else "OFF"
    bot.reply_to(msg, f"Mode: {mode}")


@bot.message_handler(content_types=['photo'])
def photo_handler(msg):
    global replace_photo, waiting_photo

    user_id = msg.from_user.id

    # 👉 Set Photo mode
    if waiting_photo and user_id == ADMIN_ID:
        replace_photo = msg.photo[-1].file_id
        waiting_photo = False
        bot.reply_to(msg, "Saved ✅")
        return

    caption = msg.caption or ""
    links = extract_links(caption)

    if not links:
        bot.reply_to(msg, "Links ഇല്ല ❌")
        return

    # 👉 Arrange links
    result = "FULL VIDEO 👀🌸\n\n"
    for i, link in enumerate(links, 1):
        result += f"VIDEO {i} ⤵️\n{link}\n\n"

    # 👉 Choose photo
    if replace_mode and replace_photo:
        photo_id = replace_photo
    else:
        photo_id = msg.photo[-1].file_id

    bot.send_photo(msg.chat.id, photo_id, caption=result)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
