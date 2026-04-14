import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# ADMINS
# =========================
ADMIN_IDS = [6630347046, 7194569468]

# =========================
# CHANNELS
# =========================
CHANNELS = {
    "Channel 1": "-1002674664027",
    "Channel 2": "-1002514181198",
    "Channel 3": "-1002427180742",
    "Channel 4": "-1003590340901",
}

# =========================
# STORAGE
# =========================
user_data = {}


# =========================
# HELPERS
# =========================
def is_admin(user_id):
    return user_id in ADMIN_IDS


def init_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "waiting_thumb": False,
            "thumb_mode": False,
            "thumb_photo": None,
            "arrange_mode": False,
            "auto_forward": False,
            "selected_channels": []
        }


def extract_links(text):
    if not text:
        return []

    matches = re.findall(r'https?://[^\s]+', text)
    cleaned = []

    for link in matches:
        link = link.strip().rstrip("),.?!;:'\"")
        if link not in cleaned:
            cleaned.append(link)

    return cleaned


def build_arranged_caption(text):
    if not text:
        return ""

    links = extract_links(text)

    if not links:
        return text[:1024]

    final_text = "FULL VIDEO 👀🌸\n\n"
    for i, link in enumerate(links, start=1):
        final_text += f"VIDEO {i} ⤵️\n{link}\n\n"

    return final_text[:1024]


def selected_channel_names(uid):
    names = []
    for name, cid in CHANNELS.items():
        if cid in user_data[uid]["selected_channels"]:
            names.append(name)
    return names


# =========================
# KEYBOARDS
# =========================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 Set Thumb", "🖼 Thumb ON")
    kb.row("❌ Thumb OFF", "🔗 Arrange ON")
    kb.row("🚫 Arrange OFF", "📢 Select Channel")
    kb.row("🟢 Auto Forward ON", "🔴 Auto Forward OFF")
    kb.row("📊 Current Settings")
    return kb


def channel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Channel 1", "Channel 2")
    kb.row("Channel 3", "Channel 4")
    kb.row("✅ Done", "🗑 Clear Channels")
    kb.row("⬅️ Back")
    return kb


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.reply_to(message, "❌ Admin only bot")
        return

    init_user(uid)
    bot.send_message(
        message.chat.id,
        "🔥 Thumb Change + Arrange Link Bot Ready ✅\n\n"
        "Functions separate ആണ്:\n"
        "1. Thumb Change = photo മാത്രം change\n"
        "2. Arrange Link = links മാത്രം arrange\n"
        "3. രണ്ടും ON ആണെങ്കിൽ രണ്ടും ചെയ്യും\n\n"
        "Buttons use ചെയ്യൂ 👇",
        reply_markup=main_kb()
    )


# =========================
# THUMB CONTROLS
# =========================
@bot.message_handler(func=lambda m: m.text == "📸 Set Thumb")
def set_thumb(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["waiting_thumb"] = True
    bot.send_message(message.chat.id, "Thumb ആയി save ചെയ്യാൻ photo അയക്കൂ 📸", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🖼 Thumb ON")
def thumb_on(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    if not user_data[uid]["thumb_photo"]:
        bot.send_message(message.chat.id, "ആദ്യം 📸 Set Thumb ചെയ്ത് photo save ചെയ്യൂ ❌", reply_markup=main_kb())
        return

    user_data[uid]["thumb_mode"] = True
    bot.send_message(message.chat.id, "Thumb Change ON ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "❌ Thumb OFF")
def thumb_off(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_mode"] = False
    bot.send_message(message.chat.id, "Thumb Change OFF ❌", reply_markup=main_kb())


# =========================
# ARRANGE CONTROLS
# =========================
@bot.message_handler(func=lambda m: m.text == "🔗 Arrange ON")
def arrange_on(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = True
    bot.send_message(message.chat.id, "Arrange Link ON ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🚫 Arrange OFF")
def arrange_off(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = False
    bot.send_message(message.chat.id, "Arrange Link OFF ❌", reply_markup=main_kb())


# =========================
# CHANNEL SELECT
# =========================
@bot.message_handler(func=lambda m: m.text == "📢 Select Channel")
def select_channel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    bot.send_message(message.chat.id, "Forward ചെയ്യേണ്ട channels select ചെയ്യൂ 👇", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text in CHANNELS.keys())
def channel_toggle(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    name = message.text
    cid = CHANNELS[name]

    if cid in user_data[uid]["selected_channels"]:
        user_data[uid]["selected_channels"].remove(cid)
        bot.send_message(message.chat.id, f"{name} removed ❌", reply_markup=channel_kb())
    else:
        user_data[uid]["selected_channels"].append(cid)
        bot.send_message(message.chat.id, f"{name} added ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text == "✅ Done")
def done_channels(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(message.chat.id, "Channels saved ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🗑 Clear Channels")
def clear_channels(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["selected_channels"] = []
    bot.send_message(message.chat.id, "Channels cleared ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text == "⬅️ Back")
def back_btn(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(message.chat.id, "Main menu ✅", reply_markup=main_kb())


# =========================
# AUTO FORWARD
# =========================
@bot.message_handler(func=lambda m: m.text == "🟢 Auto Forward ON")
def auto_forward_on(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = True
    bot.send_message(message.chat.id, "Auto Forward ON ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🔴 Auto Forward OFF")
def auto_forward_off(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = False
    bot.send_message(message.chat.id, "Auto Forward OFF ❌", reply_markup=main_kb())


# =========================
# CURRENT SETTINGS
# =========================
@bot.message_handler(func=lambda m: m.text == "📊 Current Settings")
def current_settings(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    thumb_saved = "Yes ✅" if user_data[uid]["thumb_photo"] else "No ❌"
    thumb_mode = "ON ✅" if user_data[uid]["thumb_mode"] else "OFF ❌"
    arrange_mode = "ON ✅" if user_data[uid]["arrange_mode"] else "OFF ❌"
    auto_forward = "ON ✅" if user_data[uid]["auto_forward"] else "OFF ❌"

    channels = selected_channel_names(uid)
    channels_text = "\n".join(channels) if channels else "None ❌"

    text = (
        f"Thumb Saved: {thumb_saved}\n"
        f"Thumb Mode: {thumb_mode}\n"
        f"Arrange Mode: {arrange_mode}\n"
        f"Auto Forward: {auto_forward}\n\n"
        f"Selected Channels:\n{channels_text}"
    )

    bot.send_message(message.chat.id, text, reply_markup=main_kb())


# =========================
# PHOTO HANDLER
# =========================
@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    incoming_photo = message.photo[-1].file_id
    caption = message.caption or ""

    # Save thumb photo
    if user_data[uid]["waiting_thumb"]:
        user_data[uid]["thumb_photo"] = incoming_photo
        user_data[uid]["waiting_thumb"] = False
        bot.send_photo(
            message.chat.id,
            incoming_photo,
            caption="Thumb saved ✅",
            reply_markup=main_kb()
        )
        return

    # Thumb Change function
    send_photo = incoming_photo
    if user_data[uid]["thumb_mode"] and user_data[uid]["thumb_photo"]:
        send_photo = user_data[uid]["thumb_photo"]

    # Arrange Link function
    final_caption = caption[:1024] if caption else ""
    if user_data[uid]["arrange_mode"]:
        final_caption = build_arranged_caption(caption)

    # Send back to admin
    bot.send_photo(
        message.chat.id,
        send_photo,
        caption=final_caption,
        reply_markup=main_kb()
    )

    # Auto forward to selected channels
    if user_data[uid]["auto_forward"]:
        for ch in user_data[uid]["selected_channels"]:
            try:
                bot.send_photo(ch, send_photo, caption=final_caption)
            except Exception as e:
                print("Forward photo error:", e)


# =========================
# TEXT HANDLER
# =========================
@bot.message_handler(content_types=["text"])
def text_handler(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    ignore = {
        "📸 Set Thumb", "🖼 Thumb ON", "❌ Thumb OFF",
        "🔗 Arrange ON", "🚫 Arrange OFF",
        "📢 Select Channel", "🟢 Auto Forward ON", "🔴 Auto Forward OFF",
        "📊 Current Settings", "Channel 1", "Channel 2",
        "Channel 3", "Channel 4", "✅ Done", "🗑 Clear Channels", "⬅️ Back"
    }

    if message.text in ignore:
        return

    final_text = message.text

    # Arrange Link function for text-only messages
    if user_data[uid]["arrange_mode"]:
        final_text = build_arranged_caption(message.text)

    # If thumb mode ON and thumb saved, send as photo with caption
    if user_data[uid]["thumb_mode"] and user_data[uid]["thumb_photo"]:
        bot.send_photo(
            message.chat.id,
            user_data[uid]["thumb_photo"],
            caption=final_text[:1024],
            reply_markup=main_kb()
        )

        if user_data[uid]["auto_forward"]:
            for ch in user_data[uid]["selected_channels"]:
                try:
                    bot.send_photo(ch, user_data[uid]["thumb_photo"], caption=final_text[:1024])
                except Exception as e:
                    print("Forward text-photo error:", e)

    else:
        bot.send_message(
            message.chat.id,
            final_text[:4096],
            reply_markup=main_kb()
        )

        if user_data[uid]["auto_forward"]:
            for ch in user_data[uid]["selected_channels"]:
                try:
                    bot.send_message(ch, final_text[:4096])
                except Exception as e:
                    print("Forward text error:", e)


print("Bot running...")
bot.remove_webhook()
bot.infinity_polling(skip_pending=True, none_stop=True)
