import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_IDS = [6630347046, 7194569468]
user_settings = {}

CHANNELS = {
    "Channel 1": "-1002674664027",
    "Channel 2": "-1002514181198",
    "Channel 3": "-1002427180742",
    "Channel 4": "-1003590340901",
}

PHOTO_SLOTS = ["Photo 1", "Photo 2", "Photo 3", "Photo 4", "Photo 5"]


def is_admin(user_id):
    return user_id in ADMIN_IDS


def init_user(uid):
    if uid not in user_settings:
        user_settings[uid] = {
            "saved_photos": {
                "Photo 1": None,
                "Photo 2": None,
                "Photo 3": None,
                "Photo 4": None,
                "Photo 5": None,
            },
            "selected_photo": None,
            "link_mode": False,
            "thumb_mode": False,
            "auto_forward": False,
            "selected_channels": [],
            "waiting_photo_slot": None,
            "menu": "main",
        }


def extract_links(text):
    if not text:
        return []
    return re.findall(r'https?://\S+', text)


def build_arranged_text(links):
    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)

    final_text = "LINKS\n\n"
    for i, link in enumerate(unique_links, start=1):
        final_text += f"ITEM {i}\n{link}\n\n"
    return final_text


def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔗 Link Arrangement")
    kb.row("📊 Current Settings")
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
        "Welcome\n\n"
        "Use this bot to arrange normal links cleanly.",
        reply_markup=main_kb()
    )


@bot.message_handler(func=lambda m: not is_admin(m.from_user.id), content_types=[
    "text", "photo", "video", "document", "audio", "voice", "sticker"
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
        "HOW TO USE\n\n"
        "1. Open Link Arrangement\n"
        "2. Turn ON link mode\n"
        "3. Send photo + links, or text + links\n"
        "4. Bot removes extra text and arranges links",
        reply_markup=main_kb()
    )


@bot.message_handler(func=lambda m: m.text == "📊 Current Settings")
def current_settings(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    settings = user_settings[uid]

    link_mode = "ON ✅" if settings["link_mode"] else "OFF ❌"
    thumb_mode = "ON ✅" if settings["thumb_mode"] else "OFF ❌"
    auto_forward = "ON ✅" if settings["auto_forward"] else "OFF ❌"
    selected_photo = settings["selected_photo"] or "None ❌"

    if settings["selected_channels"]:
        channels = "\n".join(settings["selected_channels"])
    else:
        channels = "None ❌"

    text = (
        "📊 CURRENT SETTINGS\n\n"
        f"🔗 Link Mode: {link_mode}\n"
        f"🖼️ Thumb Mode: {thumb_mode}\n"
        f"📈 Auto Forward: {auto_forward}\n"
        f"📸 Selected Photo: {selected_photo}\n\n"
        f"📢 Channels:\n{channels}"
    )

    bot.send_message(message.chat.id, text, reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "⬅️ Back")
def back_btn(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_settings[uid]["menu"] = "main"
    bot.send_message(message.chat.id, "Main menu ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🔗 Link Arrangement")
def link_menu(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_settings[uid]["menu"] = "link"
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

    final_text = build_arranged_text(links)

    try:
        bot.send_photo(
            message.chat.id,
            photo_id,
            caption=final_text,
            reply_markup=main_kb()
        )
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
        "📊 Current Settings",
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

    final_text = build_arranged_text(links)

    try:
        bot.send_message(
            message.chat.id,
            final_text,
            reply_markup=main_kb()
        )
    except Exception as e:
        print("Text send error:", e)


print("Bot running...")
bot.infinity_polling(skip_pending=True)
