import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_IDS = [6630347046, 7194569468]
user_settings = {}


def is_admin(user_id):
    return user_id in ADMIN_IDS


def init_user(uid):
    if uid not in user_settings:
        user_settings[uid] = {
            "link_mode": False
        }


def extract_links(text):
    if not text:
        return []
    return re.findall(r'https?://\S+', text)


def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔗 Link Arrangement")
    kb.row("❓ Help")
    return kb


def link_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🟢 Link Arrange ON", "🔴 Link Arrange OFF")
    kb.row("⬅️ Back")
    return kb


@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id

    if not is_admin(uid):
        bot.reply_to(message, "❌ Admin only bot")
        return

    init_user(uid)
    bot.send_message(
        message.chat.id,
        "🔥 Welcome\n\n"
        "🔗 Link arrange bot\n"
        "Each message = separate arranged output\n\n"
        "Use buttons below.",
        reply_markup=main_kb()
    )


@bot.message_handler(func=lambda m: not is_admin(m.from_user.id), content_types=[
    'text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker'
])
def block_non_admin(message):
    bot.reply_to(message, "❌ Admin only bot")


@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_menu(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(
        message.chat.id,
        "📌 HOW TO USE\n\n"
        "1. Click 🔗 Link Arrangement\n"
        "2. Turn ON link mode\n"
        "3. Send one message with photo + links, or text + links\n"
        "4. Bot sends one arranged reply for that one message\n\n"
        "Each message is handled separately.",
        reply_markup=main_kb()
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Back")
def back_btn(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    bot.send_message(message.chat.id, "Main menu ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🔗 Link Arrangement")
def link_menu(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    bot.send_message(message.chat.id, "Link Arrangement settings", reply_markup=link_kb())


@bot.message_handler(func=lambda m: m.text == "🟢 Link Arrange ON")
def link_on(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_settings[uid]["link_mode"] = True
    bot.send_message(message.chat.id, "Link Arrange ON ✅", reply_markup=link_kb())


@bot.message_handler(func=lambda m: m.text == "🔴 Link Arrange OFF")
def link_off(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_settings[uid]["link_mode"] = False
    bot.send_message(message.chat.id, "Link Arrange OFF ❌", reply_markup=link_kb())


@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    if not user_settings[uid]["link_mode"]:
        return

    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    links = extract_links(caption)

    if not links:
        return

    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)

    final_text = "FULL VIDEO 👀🌸\n\n"
    for i, link in enumerate(unique_links, start=1):
        final_text += f"VIDEO {i} ⤵️\n{link}\n\n"

    try:
        bot.send_photo(message.chat.id, photo_id, caption=final_text)
    except Exception as e:
        print("Photo send error:", e)


@bot.message_handler(content_types=["text"])
def text_handler(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    ignore = {
        "🔗 Link Arrangement",
        "❓ Help",
        "🟢 Link Arrange ON",
        "🔴 Link Arrange OFF",
        "⬅️ Back"
    }

    if message.text in ignore:
        return

    if not user_settings[uid]["link_mode"]:
        return

    links = extract_links(message.text)
    if not links:
        return

    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)

    final_text = "FULL VIDEO 👀🌸\n\n"
    for i, link in enumerate(unique_links, start=1):
        final_text += f"VIDEO {i} ⤵️\n{link}\n\n"

    try:
        bot.send_message(message.chat.id, final_text)
    except Exception as e:
        print("Text send error:", e)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
