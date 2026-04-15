import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_IDS = [6630347046, 7194569468]

CHANNELS = {
    "Channel 1": "-1002674664027",
    "Channel 2": "-1002514181198",
    "Channel 3": "-1002427180742",
    "Channel 4": "-1003590340901",
    "channel 5": "-1002852893991",
    }

THUMB_SLOTS = ["Photo 1", "Photo 2", "Photo 3", "Photo 4"]

user_data = {}


# =========================
# BASIC
# =========================
def is_admin(uid):
    return uid in ADMIN_IDS


def init_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "thumb_mode": False,
            "arrange_mode": False,
            "text_edit_mode": False,
            "auto_forward": False,
            "selected_channels": [],
            "selected_thumb": None,
            "waiting_thumb": None,
            "thumb_action": None,
            "thumbs": {slot: None for slot in THUMB_SLOTS},
        }


# =========================
# HELPERS
# =========================
def extract_links(text):
    return re.findall(r'https?://\S+', text or "")


def build_links(links):
    txt = ""
    for i, link in enumerate(links, 1):
        txt += f"VIDEO {i} ⤵️\n{link}\n\n"
    return txt.strip()


def arrange(text):
    links = extract_links(text)
    if not links:
        return (text or "")[:1024]
    return build_links(links)[:1024]


def extract_malayalam(text):
    lines = (text or "").splitlines()
    result = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # skip links
        if re.search(r'https?://', line):
            continue

        # keep only Malayalam lines
        if re.search(r'[\u0D00-\u0D7F]', line):
            result.append(line)

    # HEADER REMOVE
    if len(result) > 1:
        result = result[1:]

    # FOOTER REMOVE
    if len(result) > 2:
        result = result[:-2]
    elif len(result) > 1:
        result = result[:-1]

    return result


def text_edit(text):
    mal = extract_malayalam(text)
    links = extract_links(text)

    final = ""

    if mal:
        final += "\n".join(mal).strip()

    if links:
        if final:
            final += "\n\n"
        final += build_links(links)

    return final[:1024].strip()


def get_thumb(uid):
    slot = user_data[uid]["selected_thumb"]
    if not slot:
        return None
    return user_data[uid]["thumbs"].get(slot)


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
    kb.row("📸 Set Thumb", "✅ Use Thumb")
    kb.row("🖼 Thumb ON", "❌ Thumb OFF")
    kb.row("🔗 Arrange ON", "🚫 Arrange OFF")
    kb.row("📝 Text Edit ON", "❎ Text Edit OFF")
    kb.row("📢 Select Channel")
    kb.row("🟢 Auto Forward ON", "🔴 Auto Forward OFF")
    kb.row("👁 Current Thumb", "📊 Current Settings")
    return kb


def slot_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Photo 1", "Photo 2")
    kb.row("Photo 3", "Photo 4")
    kb.row("⬅️ Back")
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
def start(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ Admin only bot")
        return

    init_user(uid)
    bot.send_message(
        m.chat.id,
        "🔥 POWER BOT READY ✅\n\n"
        "• Thumb Change\n"
        "• Arrange Link\n"
        "• Text Edit\n"
        "• Header Remove\n"
        "• Footer Remove\n"
        "• Auto Forward\n\n"
        "Buttons use ചെയ്യൂ 👇",
        reply_markup=main_kb()
    )


# =========================
# THUMB SET / USE
# =========================
@bot.message_handler(func=lambda m: m.text == "📸 Set Thumb")
def set_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_action"] = "set"
    bot.send_message(m.chat.id, "Save ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.text == "✅ Use Thumb")
def use_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_action"] = "use"
    bot.send_message(m.chat.id, "Use ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.text in THUMB_SLOTS)
def thumb_slot(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    slot = m.text

    if user_data[uid]["thumb_action"] == "set":
        user_data[uid]["waiting_thumb"] = slot
        bot.send_message(m.chat.id, f"{slot} ലേക്ക് save ചെയ്യാൻ photo അയക്കൂ 📸", reply_markup=slot_kb())
        return

    if user_data[uid]["thumb_action"] == "use":
        if user_data[uid]["thumbs"].get(slot):
            user_data[uid]["selected_thumb"] = slot
            bot.send_message(m.chat.id, f"{slot} selected ✅", reply_markup=main_kb())
        else:
            bot.send_message(m.chat.id, f"{slot} il thumb ഇല്ല ❌", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.text == "👁 Current Thumb")
def current_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    thumb = get_thumb(uid)
    slot = user_data[uid]["selected_thumb"]

    if not thumb:
        bot.send_message(m.chat.id, "Current thumb ഇല്ല ❌", reply_markup=main_kb())
        return

    bot.send_photo(
        m.chat.id,
        thumb,
        caption=f"Current Thumb: {slot} ✅",
        reply_markup=main_kb()
    )


# =========================
# MODES
# =========================
@bot.message_handler(func=lambda m: m.text == "🖼 Thumb ON")
def thumb_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    if not user_data[uid]["selected_thumb"]:
        bot.send_message(m.chat.id, "ആദ്യം ✅ Use Thumb ചെയ്ത് thumb select ചെയ്യൂ ❌", reply_markup=main_kb())
        return

    user_data[uid]["thumb_mode"] = True
    bot.reply_to(m, "Thumb ON ✅")


@bot.message_handler(func=lambda m: m.text == "❌ Thumb OFF")
def thumb_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_mode"] = False
    bot.reply_to(m, "Thumb OFF ❌")


@bot.message_handler(func=lambda m: m.text == "🔗 Arrange ON")
def arrange_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = True
    bot.reply_to(m, "Arrange ON ✅")


@bot.message_handler(func=lambda m: m.text == "🚫 Arrange OFF")
def arrange_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = False
    bot.reply_to(m, "Arrange OFF ❌")


@bot.message_handler(func=lambda m: m.text == "📝 Text Edit ON")
def text_edit_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = True
    bot.reply_to(m, "Text Edit ON 🔥")


@bot.message_handler(func=lambda m: m.text == "❎ Text Edit OFF")
def text_edit_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = False
    bot.reply_to(m, "Text Edit OFF ❌")


@bot.message_handler(func=lambda m: m.text == "🟢 Auto Forward ON")
def auto_forward_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = True
    bot.reply_to(m, "Auto Forward ON ✅")


@bot.message_handler(func=lambda m: m.text == "🔴 Auto Forward OFF")
def auto_forward_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = False
    bot.reply_to(m, "Auto Forward OFF ❌")


# =========================
# CHANNELS
# =========================
@bot.message_handler(func=lambda m: m.text == "📢 Select Channel")
def select_channel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    bot.send_message(m.chat.id, "Channels select ചെയ്യൂ 👇", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text in CHANNELS.keys())
def toggle_channel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    cid = CHANNELS[m.text]

    if cid in user_data[uid]["selected_channels"]:
        user_data[uid]["selected_channels"].remove(cid)
        bot.send_message(m.chat.id, f"{m.text} removed ❌", reply_markup=channel_kb())
    else:
        user_data[uid]["selected_channels"].append(cid)
        bot.send_message(m.chat.id, f"{m.text} added ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text == "✅ Done")
def done_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(m.chat.id, "Channels saved ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "🗑 Clear Channels")
def clear_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["selected_channels"] = []
    bot.send_message(m.chat.id, "Channels cleared ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.text == "⬅️ Back")
def back_btn(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(m.chat.id, "Main menu ✅", reply_markup=main_kb())


# =========================
# SETTINGS
# =========================
@bot.message_handler(func=lambda m: m.text == "📊 Current Settings")
def current_settings(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    channel_names = selected_channel_names(uid)
    channel_text = "\n".join(channel_names) if channel_names else "None ❌"

    text = (
        f"Thumb Mode: {'ON ✅' if user_data[uid]['thumb_mode'] else 'OFF ❌'}\n"
        f"Arrange Mode: {'ON ✅' if user_data[uid]['arrange_mode'] else 'OFF ❌'}\n"
        f"Text Edit Mode: {'ON ✅' if user_data[uid]['text_edit_mode'] else 'OFF ❌'}\n"
        f"Auto Forward: {'ON ✅' if user_data[uid]['auto_forward'] else 'OFF ❌'}\n"
        f"Selected Thumb: {user_data[uid]['selected_thumb'] or 'None ❌'}\n\n"
        f"Selected Channels:\n{channel_text}"
    )
    bot.send_message(m.chat.id, text, reply_markup=main_kb())


# =========================
# PHOTO HANDLER
# =========================
@bot.message_handler(content_types=["photo"])
def photo_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    photo_id = m.photo[-1].file_id
    caption = m.caption or ""

    # save thumb
    if user_data[uid]["waiting_thumb"]:
        slot = user_data[uid]["waiting_thumb"]
        user_data[uid]["thumbs"][slot] = photo_id
        user_data[uid]["waiting_thumb"] = None
        bot.send_message(m.chat.id, f"{slot} saved ✅", reply_markup=main_kb())
        return

    send_photo = photo_id
    if user_data[uid]["thumb_mode"]:
        thumb = get_thumb(uid)
        if thumb:
            send_photo = thumb

    final_caption = caption
    if user_data[uid]["text_edit_mode"]:
        final_caption = text_edit(caption)
    elif user_data[uid]["arrange_mode"]:
        final_caption = arrange(caption)

    bot.send_photo(
        m.chat.id,
        send_photo,
        caption=final_caption[:1024],
        reply_markup=main_kb()
    )

    if user_data[uid]["auto_forward"]:
        for ch in user_data[uid]["selected_channels"]:
            try:
                bot.send_photo(ch, send_photo, caption=final_caption[:1024])
            except Exception as e:
                print("Forward photo error:", e)


# =========================
# TEXT HANDLER
# =========================
@bot.message_handler(content_types=["text"])
def text_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    ignore = {
        "📸 Set Thumb", "✅ Use Thumb",
        "🖼 Thumb ON", "❌ Thumb OFF",
        "🔗 Arrange ON", "🚫 Arrange OFF",
        "📝 Text Edit ON", "❎ Text Edit OFF",
        "📢 Select Channel",
        "🟢 Auto Forward ON", "🔴 Auto Forward OFF",
        "👁 Current Thumb", "📊 Current Settings",
        "Channel 1", "Channel 2", "Channel 3", "Channel 4",
        "✅ Done", "🗑 Clear Channels", "⬅️ Back",
        "Photo 1", "Photo 2", "Photo 3", "Photo 4"
    }

    if m.text in ignore:
        return

    txt = m.text

    if user_data[uid]["text_edit_mode"]:
        txt = text_edit(txt)
    elif user_data[uid]["arrange_mode"]:
        txt = arrange(txt)

    if user_data[uid]["thumb_mode"]:
        thumb = get_thumb(uid)
        if thumb:
            bot.send_photo(m.chat.id, thumb, caption=txt[:1024], reply_markup=main_kb())

            if user_data[uid]["auto_forward"]:
                for ch in user_data[uid]["selected_channels"]:
                    try:
                        bot.send_photo(ch, thumb, caption=txt[:1024])
                    except Exception as e:
                        print("Forward text-photo error:", e)
            return

    bot.send_message(m.chat.id, txt[:4096], reply_markup=main_kb())

    if user_data[uid]["auto_forward"]:
        for ch in user_data[uid]["selected_channels"]:
            try:
                bot.send_message(ch, txt[:4096])
            except Exception as e:
                print("Forward text error:", e)


print("Bot running...")
bot.remove_webhook()
bot.infinity_polling(skip_pending=True, none_stop=True)
