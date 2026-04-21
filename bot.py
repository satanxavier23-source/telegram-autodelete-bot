import os
import re
import json
import time
import telebot
import threading
import logging
from telebot import types

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

ADMIN_IDS = [6630347046, 7194569468]

CHANNELS = {
    "Channel 1": -1002674664027,
    "Channel 2": -1002514181198,
    "Channel 3": -1002427180742,
    "Channel 4": -1003590340901,
    "Channel 5": -1002852893991,
}

THUMB_SLOTS = ["Photo 1", "Photo 2", "Photo 3", "Photo 4"]
DATA_FILE = "user_data.json"

user_data = {}
data_lock = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# SAVE / LOAD
# =========================
def default_user_state():
    return {
        "thumb_mode": False,
        "arrange_mode": False,
        "text_edit_mode": False,
        "middle_mode": False,
        "keep_text_mode": False,
        "auto_forward": False,
        "remove_header_mode": False,
        "remove_footer_mode": False,
        "selected_channels": [],
        "selected_thumb": None,
        "waiting_thumb": None,
        "thumb_action": None,
        "thumbs": {slot: None for slot in THUMB_SLOTS},
    }


def save_data():
    try:
        with data_lock:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Save data error: {e}")


def load_data():
    global user_data
    try:
        if not os.path.exists(DATA_FILE):
            user_data = {}
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        fixed = {}
        for uid_str, value in raw.items():
            uid = int(uid_str)
            base = default_user_state()
            base.update(value)

            if "thumbs" not in base or not isinstance(base["thumbs"], dict):
                base["thumbs"] = {slot: None for slot in THUMB_SLOTS}
            else:
                for slot in THUMB_SLOTS:
                    if slot not in base["thumbs"]:
                        base["thumbs"][slot] = None

            fixed[uid] = base

        user_data = fixed
        logging.info("User data loaded successfully")
    except Exception as e:
        logging.error(f"Load data error: {e}")
        user_data = {}


# =========================
# BASIC
# =========================
def is_admin(uid):
    return uid in ADMIN_IDS


def init_user(uid):
    with data_lock:
        if uid not in user_data:
            user_data[uid] = default_user_state()
    save_data()


# =========================
# HELPERS
# =========================
def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def extract_links(text):
    return re.findall(r'https?://[^\s<>()"]+', text or "")


def unique_keep_order(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_links(links):
    links = unique_keep_order(links)
    if not links:
        return ""
    return "\n\n".join([f"Video {i}\n{link}" for i, link in enumerate(links, 1)]).strip()


def safe_caption(text):
    return (text or "")[:1024]


def safe_text(text):
    return (text or "")[:4096]


def has_malayalam(text):
    return bool(re.search(r"[\u0D00-\u0D7F]", text or ""))


def only_symbols_or_emoji(line):
    return bool(re.fullmatch(r"[\W_🔥💥⚜️❤️✅🥰😍😘💎✨⭐🎉💯😂🤣🙏👉📌📍📢•○●◇◆■□~`|]+", line or ""))


def is_link_line(line):
    return bool(re.search(r"https?://", line or ""))


def is_header_like(line: str) -> bool:
    line = normalize_line(line)
    if not line:
        return True

    lower = line.lower()

    exact_keywords = [
        "join our terabox channel",
        "rasikan bro",
        "watch video",
        "terabox channel",
        "join our whatsapp channel",
    ]
    for word in exact_keywords:
        if word in lower:
            return True

    if lower.startswith("@") and len(line) < 40:
        return True

    promo_words = ["join", "telegram", "whatsapp", "subscribe", "follow"]
    if any(word in lower for word in promo_words) and len(line) < 80:
        return True

    emoji_count = len(re.findall(r"[🔥💥⚜️❤️✅🥰😍😘💎✨⭐🎉💯📢📌👉]", line))
    if emoji_count >= 3 and len(line) < 60:
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
        "join our",
        "telegram channel",
        "whatsapp channel",
        "follow us",
        "subscribe",
        "like",
        "share",
        "comment",
        "reaction",
        "our channel",
        "terabox channel",
        "കൂടുതൽ",
        "വീഡിയോകൾക്കായി",
        "ചാനൽ",
        "സബ്സ്ക്രൈബ്",
        "ഫോളോ",
        "ലൈക്ക്",
        "ലൈക്കുകൾ",
        "ഷെയർ",
        "കമന്റ്",
        "ഞങ്ങളുടെ",
        "നമ്മുടെ",
    ]

    if any(word in lower for word in footer_keywords) and len(line) < 120:
        return True

    if len(re.findall(r"[🔥💥⚜️❤️😂🤣💯✨📢📌👉🥰😍😘💎⭐🎉🙏]", line)) >= 4:
        return True

    if re.search(r"[_\-—=~*#]{3,}", line):
        return True

    if only_symbols_or_emoji(line):
        return True

    return False


def remove_header_footer_lines(uid, text):
    original = (text or "").strip()
    lines = (text or "").splitlines()
    cleaned = [line.rstrip() for line in lines if line.strip()]

    if not cleaned:
        return ""

    if user_data[uid]["remove_header_mode"]:
        while cleaned and is_header_like(cleaned[0]):
            cleaned.pop(0)

    if user_data[uid]["remove_footer_mode"]:
        while cleaned and is_footer_like(cleaned[-1]):
            cleaned.pop()

    result = "\n".join(cleaned).strip()
    return result if result else original


def clean_lines_keep_malayalam(uid, text):
    lines = (text or "").splitlines()
    cleaned = []

    for raw in lines:
        line = normalize_line(raw)
        if not line:
            continue

        if is_link_line(line):
            continue

        if re.match(r"^\d+[\).\s]", line):
            continue

        if re.search(r"[A-Za-z]", line) and not has_malayalam(line):
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

    if user_data[uid]["remove_header_mode"]:
        while cleaned and is_header_like(cleaned[0]):
            cleaned.pop(0)

    if user_data[uid]["remove_footer_mode"]:
        while cleaned and is_footer_like(cleaned[-1]):
            cleaned.pop()

    return unique_keep_order(cleaned)


def middle_text_filter(text):
    lines = (text or "").splitlines()
    result = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.search(r"https?://", line):
            continue

        if re.fullmatch(r"[\W_🔥💥⚜️❤️😂🤣💯✨📢📌👉✅🥰😍😘💎⭐🎉🙏•○●◇◆■□~`|_]+", line):
            continue

        if any(w in line for w in [
            "ലൈക്ക്", "ലൈക്കുകൾ", "ഉഷാർ", "പരിപാടി",
            "ചാനൽ", "സബ്സ്ക്രൈബ്", "ഫോളോ"
        ]):
            continue

        if has_malayalam(line):
            result.append(line)

    if len(result) >= 1:
        result = result[1:]

    return result


def arrange(text):
    links = extract_links(text)
    if not links:
        return safe_text((text or "").strip())
    return safe_text(build_links(links))


def text_edit(uid, text):
    mal_lines = clean_lines_keep_malayalam(uid, text)
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


def keep_text_and_links(uid, text):
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if user_data[uid]["remove_header_mode"]:
        while lines and is_header_like(lines[0]):
            lines.pop(0)

    if user_data[uid]["remove_footer_mode"]:
        while lines and is_footer_like(lines[-1]):
            lines.pop()

    bracket_text = None
    for line in lines:
        match = re.search(r"\[(.*?)\]", line)
        if match:
            bracket_text = f"[{match.group(1).strip()}]"
            break

    links = []
    for line in lines:
        found = re.findall(r'https?://[^\s<>()"]+', line)
        for url in found:
            if url not in links:
                links.append(url)

    main_text_lines = []
    ignore_patterns = [
        r"join",
        r"join our",
        r"terabox channel",
        r"whatsapp channel",
        r"follow",
        r"subscribe",
        r"watch video",
        r"video\s*\d+",
        r"^https?://",
        r"^\.$",
        r"^🆔$",
        r"rasikan bro",
        r"കൂടുതൽ വീഡിയോകൾക്കായി",
        r"സബ്സ്ക്രൈബ്",
    ]

    for line in lines:
        low = line.lower()

        if re.search(r"https?://", line):
            continue

        if re.search(r"\[.*?\]", line):
            continue

        if any(re.search(p, low) for p in ignore_patterns):
            continue

        if only_symbols_or_emoji(line):
            continue

        main_text_lines.append(line)

    main_text = " ".join(unique_keep_order(main_text_lines)).strip()

    result = []
    if bracket_text:
        result.append(bracket_text)
    elif main_text:
        result.append(main_text)

    for i, link in enumerate(links, start=1):
        result.append(f"\nVideo {i}\n{link}")

    return safe_text("\n".join(result).strip())


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
    text = remove_header_footer_lines(uid, text)

    if user_data[uid]["keep_text_mode"]:
        return keep_text_and_links(uid, text)

    if user_data[uid]["middle_mode"]:
        mal = middle_text_filter(text)
        links = extract_links(text)

        parts = []
        if mal:
            parts.append("\n".join(mal))
        if links:
            parts.append(build_links(links))

        result = "\n\n".join(parts).strip()
        return safe_text(result if result else text)

    if user_data[uid]["text_edit_mode"]:
        return text_edit(uid, text)

    if user_data[uid]["arrange_mode"]:
        return arrange(text)

    return safe_text(text.strip())


def send_message_safe(chat_id, text, reply_markup=None):
    try:
        return bot.send_message(chat_id, safe_text(text), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send message error: {e}")


def send_photo_safe(chat_id, photo, caption="", reply_markup=None):
    try:
        return bot.send_photo(chat_id, photo, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send photo error: {e}")


def send_video_safe(chat_id, video, caption="", reply_markup=None):
    try:
        return bot.send_video(chat_id, video, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send video error: {e}")


def send_document_safe(chat_id, document, caption="", reply_markup=None):
    try:
        return bot.send_document(chat_id, document, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send document error: {e}")


def send_animation_safe(chat_id, animation, caption="", reply_markup=None):
    try:
        return bot.send_animation(chat_id, animation, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send animation error: {e}")


def forward_to_channels_text(uid, text):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        send_message_safe(ch, text)


def forward_to_channels_photo(uid, photo, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        send_photo_safe(ch, photo, caption=caption)


def forward_to_channels_video(uid, video, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        send_video_safe(ch, video, caption=caption)


def forward_to_channels_document(uid, document, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        send_document_safe(ch, document, caption=caption)


def forward_to_channels_animation(uid, animation, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        send_animation_safe(ch, animation, caption=caption)


# =========================
# KEYBOARDS
# =========================
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📸 Set Thumb", "✅ Use Thumb")
    kb.row("🖼 Thumb ON", "🖼 Thumb OFF")
    kb.row("🔗 Arrange ON", "🔗 Arrange OFF")
    kb.row("🧲 Keep Text ON", "🧲 Keep Text OFF")
    kb.row("📝 Text Edit ON", "📝 Text Edit OFF")
    kb.row("🎯 Middle ON", "🎯 Middle OFF")
    kb.row("🧹 Header Remove ON", "🧹 Header Remove OFF")
    kb.row("✂️ Footer Remove ON", "✂️ Footer Remove OFF")
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
    send_message_safe(
        m.chat.id,
        "🔥 SMART FILTER BOT READY ✅\n\n"
        "• Thumb Change\n"
        "• Arrange Link\n"
        "• Keep Text + Links\n"
        "• Text Edit\n"
        "• Middle Text Mode\n"
        "• Header Remove\n"
        "• Footer Remove\n"
        "• Auto Forward\n"
        "• Photo / Video / Document / Animation Support\n"
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
    save_data()
    send_message_safe(m.chat.id, "Save ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✅ Use Thumb")
def use_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_action"] = "use"
    save_data()
    send_message_safe(m.chat.id, "Use ചെയ്യാൻ slot select ചെയ്യൂ", reply_markup=slot_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text in THUMB_SLOTS)
def thumb_slot(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    slot = m.text
    action = user_data[uid]["thumb_action"]

    if action == "set":
        user_data[uid]["waiting_thumb"] = slot
        save_data()
        send_message_safe(m.chat.id, f"{slot} ലേക്ക് save ചെയ്യാൻ photo അയക്കൂ 📸", reply_markup=slot_kb())
        return

    if action == "use":
        if user_data[uid]["thumbs"].get(slot):
            user_data[uid]["selected_thumb"] = slot
            user_data[uid]["thumb_action"] = None
            save_data()
            send_message_safe(m.chat.id, f"{slot} selected ✅", reply_markup=main_kb())
        else:
            send_message_safe(m.chat.id, f"{slot} il thumb ഇല്ല ❌", reply_markup=slot_kb())
        return

    send_message_safe(m.chat.id, "ആദ്യം 📸 Set Thumb അല്ലെങ്കിൽ ✅ Use Thumb press ചെയ്യൂ", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "👁 Current Thumb")
def current_thumb(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    thumb = get_thumb(uid)
    slot = user_data[uid]["selected_thumb"]

    if not thumb:
        send_message_safe(m.chat.id, "Current thumb ഇല്ല ❌", reply_markup=main_kb())
        return

    send_photo_safe(m.chat.id, thumb, caption=f"Current Thumb: {slot} ✅", reply_markup=main_kb())


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
        send_message_safe(m.chat.id, "ആദ്യം ✅ Use Thumb ചെയ്ത് thumb select ചെയ്യൂ ❌", reply_markup=main_kb())
        return

    user_data[uid]["thumb_mode"] = True
    save_data()
    bot.reply_to(m, "Thumb ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🖼 Thumb OFF")
def thumb_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["thumb_mode"] = False
    save_data()
    bot.reply_to(m, "Thumb OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔗 Arrange ON")
def arrange_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = True
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["middle_mode"] = False
    user_data[uid]["keep_text_mode"] = False
    save_data()
    bot.reply_to(m, "Arrange ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔗 Arrange OFF")
def arrange_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["arrange_mode"] = False
    save_data()
    bot.reply_to(m, "Arrange OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🧲 Keep Text ON")
def keep_text_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["keep_text_mode"] = True
    user_data[uid]["arrange_mode"] = False
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["middle_mode"] = False
    save_data()
    bot.reply_to(m, "Keep Text Mode ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🧲 Keep Text OFF")
def keep_text_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["keep_text_mode"] = False
    save_data()
    bot.reply_to(m, "Keep Text Mode OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📝 Text Edit ON")
def text_edit_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = True
    user_data[uid]["arrange_mode"] = False
    user_data[uid]["middle_mode"] = False
    user_data[uid]["keep_text_mode"] = False
    save_data()
    bot.reply_to(m, "Text Edit ON 🔥")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "📝 Text Edit OFF")
def text_edit_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["text_edit_mode"] = False
    save_data()
    bot.reply_to(m, "Text Edit OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🎯 Middle ON")
def middle_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["middle_mode"] = True
    user_data[uid]["text_edit_mode"] = False
    user_data[uid]["arrange_mode"] = False
    user_data[uid]["keep_text_mode"] = False
    save_data()
    bot.reply_to(m, "Middle Mode ON 🎯")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🎯 Middle OFF")
def middle_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["middle_mode"] = False
    save_data()
    bot.reply_to(m, "Middle Mode OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🧹 Header Remove ON")
def header_remove_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["remove_header_mode"] = True
    save_data()
    bot.reply_to(m, "Header Remove ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🧹 Header Remove OFF")
def header_remove_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["remove_header_mode"] = False
    save_data()
    bot.reply_to(m, "Header Remove OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✂️ Footer Remove ON")
def footer_remove_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["remove_footer_mode"] = True
    save_data()
    bot.reply_to(m, "Footer Remove ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✂️ Footer Remove OFF")
def footer_remove_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["remove_footer_mode"] = False
    save_data()
    bot.reply_to(m, "Footer Remove OFF ❌")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🟢 Auto Forward ON")
def auto_forward_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    if not user_data[uid]["selected_channels"]:
        send_message_safe(m.chat.id, "ആദ്യം channel select ചെയ്യൂ ❌", reply_markup=channel_kb())
        return

    user_data[uid]["auto_forward"] = True
    save_data()
    bot.reply_to(m, "Auto Forward ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔴 Auto Forward OFF")
def auto_forward_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["auto_forward"] = False
    save_data()
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
    send_message_safe(m.chat.id, "Channels select ചെയ്യൂ 👇", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text in CHANNELS.keys())
def toggle_channel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    cid = CHANNELS[m.text]

    if cid in user_data[uid]["selected_channels"]:
        user_data[uid]["selected_channels"].remove(cid)
        save_data()
        send_message_safe(m.chat.id, f"{m.text} removed ❌", reply_markup=channel_kb())
    else:
        user_data[uid]["selected_channels"].append(cid)
        save_data()
        send_message_safe(m.chat.id, f"{m.text} added ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "✅ Done")
def done_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    send_message_safe(m.chat.id, "Channels saved ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🗑 Clear Channels")
def clear_channels(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["selected_channels"] = []
    save_data()
    send_message_safe(m.chat.id, "Channels cleared ✅", reply_markup=channel_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "⬅️ Back")
def back_btn(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    send_message_safe(m.chat.id, "Main menu ✅", reply_markup=main_kb())


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
        f"Keep Text Mode: {'ON ✅' if user_data[uid]['keep_text_mode'] else 'OFF ❌'}\n"
        f"Text Edit Mode: {'ON ✅' if user_data[uid]['text_edit_mode'] else 'OFF ❌'}\n"
        f"Middle Mode: {'ON ✅' if user_data[uid]['middle_mode'] else 'OFF ❌'}\n"
        f"Header Remove: {'ON ✅' if user_data[uid]['remove_header_mode'] else 'OFF ❌'}\n"
        f"Footer Remove: {'ON ✅' if user_data[uid]['remove_footer_mode'] else 'OFF ❌'}\n"
        f"Auto Forward: {'ON ✅' if user_data[uid]['auto_forward'] else 'OFF ❌'}\n"
        f"Selected Thumb: {user_data[uid]['selected_thumb'] or 'None ❌'}\n\n"
        f"Selected Channels:\n{channel_text}"
    )
    send_message_safe(m.chat.id, text, reply_markup=main_kb())


# =========================
# PHOTO HANDLER
# =========================
@bot.message_handler(content_types=["photo"])
def photo_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    try:
        photo_id = m.photo[-1].file_id
        caption = m.caption or ""

        if user_data[uid]["waiting_thumb"]:
            slot = user_data[uid]["waiting_thumb"]
            user_data[uid]["thumbs"][slot] = photo_id
            user_data[uid]["waiting_thumb"] = None
            user_data[uid]["thumb_action"] = None
            save_data()
            send_message_safe(m.chat.id, f"{slot} saved ✅", reply_markup=main_kb())
            return

        final_text = apply_processing(uid, caption)

        send_photo_id = photo_id
        if user_data[uid]["thumb_mode"]:
            thumb = get_thumb(uid)
            if thumb:
                send_photo_id = thumb

        send_photo_safe(m.chat.id, send_photo_id, caption=final_text, reply_markup=main_kb())
        forward_to_channels_photo(uid, send_photo_id, final_text)

    except Exception as e:
        logging.error(f"Photo handler error: {e}")
        send_message_safe(m.chat.id, "Photo process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())


# =========================
# VIDEO HANDLER
# =========================
@bot.message_handler(content_types=["video"])
def video_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    try:
        video_id = m.video.file_id
        caption = m.caption or ""
        final_text = apply_processing(uid, caption)

        send_video_safe(m.chat.id, video_id, caption=final_text, reply_markup=main_kb())
        forward_to_channels_video(uid, video_id, final_text)

    except Exception as e:
        logging.error(f"Video handler error: {e}")
        send_message_safe(m.chat.id, "Video process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())


# =========================
# DOCUMENT HANDLER
# =========================
@bot.message_handler(content_types=["document"])
def document_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    try:
        doc_id = m.document.file_id
        caption = m.caption or ""
        final_text = apply_processing(uid, caption)

        send_document_safe(m.chat.id, doc_id, caption=final_text, reply_markup=main_kb())
        forward_to_channels_document(uid, doc_id, final_text)

    except Exception as e:
        logging.error(f"Document handler error: {e}")
        send_message_safe(m.chat.id, "Document process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())


# =========================
# ANIMATION HANDLER
# =========================
@bot.message_handler(content_types=["animation"])
def animation_handler(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)

    try:
        anim_id = m.animation.file_id
        caption = m.caption or ""
        final_text = apply_processing(uid, caption)

        send_animation_safe(m.chat.id, anim_id, caption=final_text, reply_markup=main_kb())
        forward_to_channels_animation(uid, anim_id, final_text)

    except Exception as e:
        logging.error(f"Animation handler error: {e}")
        send_message_safe(m.chat.id, "Animation process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())


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
        "🖼 Thumb ON", "🖼 Thumb OFF",
        "🔗 Arrange ON", "🔗 Arrange OFF",
        "🧲 Keep Text ON", "🧲 Keep Text OFF",
        "📝 Text Edit ON", "📝 Text Edit OFF",
        "🎯 Middle ON", "🎯 Middle OFF",
        "🧹 Header Remove ON", "🧹 Header Remove OFF",
        "✂️ Footer Remove ON", "✂️ Footer Remove OFF",
        "📢 Select Channel",
        "🟢 Auto Forward ON", "🔴 Auto Forward OFF",
        "👁 Current Thumb", "📊 Current Settings",
        "Channel 1", "Channel 2", "Channel 3", "Channel 4", "Channel 5",
        "✅ Done", "🗑 Clear Channels", "⬅️ Back",
        "Photo 1", "Photo 2", "Photo 3", "Photo 4"
    }

    if m.text in ignore:
        return

    try:
        final_text = apply_processing(uid, m.text)

        if user_data[uid]["thumb_mode"]:
            thumb = get_thumb(uid)
            if thumb:
                send_photo_safe(m.chat.id, thumb, caption=final_text, reply_markup=main_kb())
                forward_to_channels_photo(uid, thumb, final_text)
                return

        send_message_safe(
            m.chat.id,
            final_text if final_text else "Empty text ❌",
            reply_markup=main_kb()
        )

        if final_text:
            forward_to_channels_text(uid, final_text)

    except Exception as e:
        logging.error(f"Text handler error: {e}")
        send_message_safe(m.chat.id, "Text process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())


# =========================
# FALLBACK ERROR HANDLER
# =========================
def run_bot():
    while True:
        try:
            logging.info("Bot running...")
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            logging.error(f"Polling crash: {e}")
            time.sleep(5)


if __name__ == "__main__":
    load_data()
    run_bot()
