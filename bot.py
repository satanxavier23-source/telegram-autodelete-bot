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
    "Channel 1": -1002674664027,
    "Channel 2": -1002514181198,
    "Channel 3": -1002427180742,
    "Channel 4": -1003590340901,
    "Channel 5": -1002852893991,
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
            "ai_filter_mode": False,
            "middle_mode": False,
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
def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def extract_links(text):
    return re.findall(r'https?://[^\s]+', text or "")


def build_links(links):
    if not links:
        return ""
    out = []
    for i, link in enumerate(links, 1):
        out.append(f"VIDEO {i} ⤵️\n{link}")
    return "\n\n".join(out).strip()


def safe_caption(text):
    return (text or "")[:1024]


def safe_text(text):
    return (text or "")[:4096]


def has_malayalam(text):
    return bool(re.search(r'[\u0D00-\u0D7F]', text or ""))


def only_symbols_or_emoji(line):
    return bool(re.fullmatch(r'[\W_🔥💥⚜️❤️✅🥰😍😘💎✨⭐🎉💯😂🤣🙏👉📌📍📢•○●◇◆■□~`|]+', line or ""))


def is_link_line(line):
    return bool(re.search(r'https?://', line or ""))


def is_header_like(line: str) -> bool:
    line = normalize_line(line)
    if not line:
        return True

    lower = line.lower()

    header_keywords = [
        "join", "join our", "channel", "group",
        "telegram", "whatsapp", "follow", "subscribe",
        "latest update", "watch video", "terabox channel", "@",
        "must watch"
    ]

    for word in header_keywords:
        if word in lower:
            return True

    emoji_count = len(re.findall(r'[🔥💥⚜️❤️✅🥰😍😘💎✨⭐🎉💯📢📌👉]', line))
    if emoji_count >= 3 and len(line) < 50:
        return True

    if only_symbols_or_emoji(line):
        return True

    return False


def is_footer_like(line: str) -> bool:
    line = normalize_line(line)
    if not line:
        return True

    lower = line.lower()

    footer_keywords = [
        # english
        "join", "join our", "join our whatsapp",
        "whatsapp", "telegram", "channel", "group",
        "follow", "follow us",
        "subscribe", "support",
        "comment", "comments",
        "react", "reaction",
        "like", "likes", "share",
        "watch", "watch now", "must watch",
        "click", "our channel", "@",

        # malayalam
        "കൂടുതൽ", "വീഡിയോ", "വീഡിയോകൾക്കായി",
        "ചാനൽ", "സബ്സ്ക്രൈബ്", "ഫോളോ",
        "ലൈക്ക്", "ലൈക്കുകൾ", "ഷെയർ", "കമന്റ്",
        "ഞങ്ങളുടെ", "നമ്മുടെ", "വന്നാൽ", "ഉഷാർ", "പരിപാടി"
    ]

    for word in footer_keywords:
        if word in lower:
            return True

    if len(re.findall(r'[🔥💥⚜️❤️😂🤣💯✨📢📌👉🥰😍😘💎⭐🎉🙏]', line)) >= 3:
        return True

    if re.search(r'[_\-—=~*#]{3,}', line):
        return True

    if only_symbols_or_emoji(line):
        return True

    return False


def clean_lines_keep_malayalam(text):
    lines = (text or "").splitlines()
    cleaned = []

    for raw in lines:
        line = normalize_line(raw)
        if not line:
            continue

        if is_link_line(line):
            continue

        if re.match(r'^\d+[\).\s]', line):
            continue

        if re.search(r'[A-Za-z]', line) and not has_malayalam(line):
            continue

        if only_symbols_or_emoji(line):
            continue

        promo_words = [
            "കൂടുതൽ", "ചാനൽ", "സബ്സ്ക്രൈബ്",
            "ഫോളോ", "ലൈക്ക്", "ലൈക്കുകൾ",
            "ഷെയർ", "കമന്റ്", "വന്നാൽ",
            "ഞങ്ങളുടെ", "നമ്മുടെ", "ഉഷാർ", "പരിപാടി"
        ]
        if any(word in line for word in promo_words):
            continue

        if has_malayalam(line):
            cleaned.append(line)

    while cleaned and is_header_like(cleaned[0]):
        cleaned.pop(0)

    while cleaned and is_footer_like(cleaned[-1]):
        cleaned.pop()

    final_lines = []
    seen = set()

    for line in cleaned:
        if line not in seen:
            final_lines.append(line)
            seen.add(line)

    return final_lines


def middle_text_filter(text):
    lines = (text or "").splitlines()
    result = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.search(r'https?://', line):
            continue

        if re.fullmatch(r'[\W_🔥💥⚜️❤️😂🤣💯✨📢📌👉✅🥰😍😘💎⭐🎉🙏•○●◇◆■□~`|_]+', line):
            continue

        if any(w in line for w in [
            "ലൈക്ക്", "ലൈക്കുകൾ", "ഉഷാർ", "പരിപാടി",
            "ചാനൽ", "സബ്സ്ക്രൈബ്", "ഫോളോ"
        ]):
            continue

        if re.search(r'[\u0D00-\u0D7F]', line):
            result.append(line)

    if len(result) >= 1:
        result = result[1:]

    return result


def arrange(text):
    links = extract_links(text)
    if not links:
        return safe_text((text or "").strip())
    return safe_text(build_links(links))


def text_edit(text):
    mal_lines = clean_lines_keep_malayalam(text)
    links = extract_links(text)

    parts = []

    if mal_lines:
        parts.append("\n".join(mal_lines).strip())

    if links:
        parts.append(build_links(links))

    final = "\n\n".join([p for p in parts if p]).strip()

    if not final:
        final = (text or "").strip()

    return safe_text(final)


def smart_ai_filter(text):
    lines = (text or "").splitlines()
    links = extract_links(text)

    cleaned = []

    for i, raw in enumerate(lines):
        line = normalize_line(raw)
        if not line:
            continue

        if is_link_line(line):
            continue

        if i == 0 and is_header_like(line):
            continue

        if is_footer_like(line):
            continue

        if only_symbols_or_emoji(line):
            continue

        if re.match(r'^\d+[\).\s]', line):
            continue

        if re.search(r'[A-Za-z]', line) and not has_malayalam(line):
            continue

        if any(w in line for w in ["ലൈക്ക്", "ചാനൽ", "ഫോളോ", "വന്നാൽ", "സബ്സ്ക്രൈബ്", "കൂടുതൽ"]):
            continue

        if has_malayalam(line):
            cleaned.append(line)

    while cleaned and is_header_like(cleaned[0]):
        cleaned.pop(0)

    while cleaned and is_footer_like(cleaned[-1]):
        cleaned.pop()

    final_lines = []
    seen = set()
    for line in cleaned:
        if line not in seen:
            final_lines.append(line)
            seen.add(line)

    parts = []

    if final_lines:
        parts.append("\n".join(final_lines).strip())

    if links:
        parts.append(build_links(links))

    final = "\n\n".join([p for p in parts if p]).strip()

    if not final:
        final = (text or "").strip()

    return safe_text(final)


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


def apply_processing(uid, text):
    text = text or ""

    if user_data[uid]["middle_mode"]:
        mal = middle_text_filter(text)
        links = extract_links(text)

        parts = []

        if mal:
            parts.append("\n".join(mal))

        if links:
            parts.append(build_links(links))

        return "\n\n".join(parts).strip()[:4096]

    if user_data[uid]["ai_filter_mode"]:
        return smart_ai_filter(text)
    elif user_data[uid]["text_edit_mode"]:
        return text_edit(text)
    elif user_data[uid]["arrange_mode"]:
        return arrange(text)

    return text.strip()


def forward_to_channels_text(uid, text):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            bot.send_message(ch, safe_text(text))
        except Exception as e:
            print("Forward text error:", e)


def forward_to_channels_photo(uid, photo, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            bot.send_photo(ch, photo, caption=safe_caption(caption))
        except Exception as e:
            print("Forward photo error:", e)


# =========================
# KEYBOARDS
# =========================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 Set Thumb", "✅ Use Thumb")
    kb.row("🖼 Thumb ON", "❌ Thumb OFF")
    kb.row("🔗 Arrange ON", "🚫 Arrange OFF")
    kb.row("📝 Text Edit ON", "❎ Text Edit OFF")
    kb.row("🤖 AI Filter ON", "🛑 AI Filter OFF")
    kb.row("🎯 Middle ON", "🛑 Middle OFF")
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
    kb.row("Channel 5")
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
        "🔥 SMART AI FILTER BOT READY ✅\n\n"
        "• Thumb Change\n"
        "• Arrange Link\n"
        "• Text Edit\n"
        "• AI Smart Filter\n"
        "• Middle Text Mode\n"
        "• Auto Forward\n"
        "• Channel 1 to Channel 5\n\n"
        "Buttons use ചെയ്യൂ 👇",
        reply_markup=main_kb()
    )


# =========================
# THUMB SET / USE
# =========================
@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📸 Set Thumb")
def set_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_action"] = "set"
    bot.send_message(m.chat.id, "Save ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✅ Use Thumb")
def use_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_action"] = "use"
    bot.send_message(m.chat.id, "Use ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text in THUMB_SLOTS)
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
            user_data[uid]["thumb_action"] = None
            bot.send_message(m.chat.id, f"{slot} selected ✅", reply_markup=main_kb())
        else:
            bot.send_message(m.chat.id, f"{slot} il thumb ഇല്ല ❌", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "👁 Current Thumb")
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
@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🖼 Thumb ON")
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


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "❌ Thumb OFF")
def thumb_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_mode"] = False
    bot.reply_to(m, "Thumb OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔗 Arrange ON")
def arrange_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = True
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["ai_filter_mode"] = False
    user_data[uid]["middle_mode"] = False
    bot.reply_to(m, "Arrange ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🚫 Arrange OFF")
def arrange_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = False
    bot.reply_to(m, "Arrange OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📝 Text Edit ON")
def text_edit_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = True
    user_data[uid]["ai_filter_mode"] = False
    user_data[uid]["arrange_mode"] = False
    user_data[uid]["middle_mode"] = False
    bot.reply_to(m, "Text Edit ON 🔥")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "❎ Text Edit OFF")
def text_edit_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = False
    bot.reply_to(m, "Text Edit OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🤖 AI Filter ON")
def ai_filter_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["ai_filter_mode"] = True
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["arrange_mode"] = False
    user_data[uid]["middle_mode"] = False
    bot.reply_to(m, "AI Filter ON 🤖🔥")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🛑 AI Filter OFF")
def ai_filter_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["ai_filter_mode"] = False
    bot.reply_to(m, "AI Filter OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🎯 Middle ON")
def middle_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["middle_mode"] = True
    user_data[uid]["ai_filter_mode"] = False
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["arrange_mode"] = False
    bot.reply_to(m, "Middle Mode ON 🎯")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🛑 Middle OFF")
def middle_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["middle_mode"] = False
    bot.reply_to(m, "Middle Mode OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🟢 Auto Forward ON")
def auto_forward_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = True
    bot.reply_to(m, "Auto Forward ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔴 Auto Forward OFF")
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
@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📢 Select Channel")
def select_channel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    bot.send_message(m.chat.id, "Channels select ചെയ്യൂ 👇", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text in CHANNELS.keys())
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


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✅ Done")
def done_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(m.chat.id, "Channels saved ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🗑 Clear Channels")
def clear_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["selected_channels"] = []
    bot.send_message(m.chat.id, "Channels cleared ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "⬅️ Back")
def back_btn(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    bot.send_message(m.chat.id, "Main menu ✅", reply_markup=main_kb())


# =========================
# SETTINGS
# =========================
@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📊 Current Settings")
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
        f"AI Filter Mode: {'ON ✅' if user_data[uid]['ai_filter_mode'] else 'OFF ❌'}\n"
        f"Middle Mode: {'ON ✅' if user_data[uid]['middle_mode'] else 'OFF ❌'}\n"
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

    if user_data[uid]["waiting_thumb"]:
        slot = user_data[uid]["waiting_thumb"]
        user_data[uid]["thumbs"][slot] = photo_id
        user_data[uid]["waiting_thumb"] = None
        user_data[uid]["thumb_action"] = None
        bot.send_message(m.chat.id, f"{slot} saved ✅", reply_markup=main_kb())
        return

    final_text = apply_processing(uid, caption)

    send_photo_id = photo_id
    if user_data[uid]["thumb_mode"]:
        thumb = get_thumb(uid)
        if thumb:
            send_photo_id = thumb

    bot.send_photo(
        m.chat.id,
        send_photo_id,
        caption=safe_caption(final_text),
        reply_markup=main_kb()
    )

    forward_to_channels_photo(uid, send_photo_id, safe_caption(final_text))


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
        "🤖 AI Filter ON", "🛑 AI Filter OFF",
        "🎯 Middle ON", "🛑 Middle OFF",
        "📢 Select Channel",
        "🟢 Auto Forward ON", "🔴 Auto Forward OFF",
        "👁 Current Thumb", "📊 Current Settings",
        "Channel 1", "Channel 2", "Channel 3", "Channel 4", "Channel 5",
        "✅ Done", "🗑 Clear Channels", "⬅️ Back",
        "Photo 1", "Photo 2", "Photo 3", "Photo 4"
    }

    if m.text in ignore:
        return

    final_text = apply_processing(uid, m.text)

    if user_data[uid]["thumb_mode"]:
        thumb = get_thumb(uid)
        if thumb:
            bot.send_photo(
                m.chat.id,
                thumb,
                caption=safe_caption(final_text),
                reply_markup=main_kb()
            )
            forward_to_channels_photo(uid, thumb, safe_caption(final_text))
            return

    bot.send_message(
        m.chat.id,
        safe_text(final_text) if final_text else "Empty text ❌",
        reply_markup=main_kb()
    )

    if final_text:
        forward_to_channels_text(uid, safe_text(final_text))


print("Bot running...")
bot.remove_webhook()
bot.infinity_polling(skip_pending=True, none_stop=True)
