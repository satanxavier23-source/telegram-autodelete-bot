import os
import re
import json
import time
import shutil
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
BACKUP_FILE = "user_data_backup.json"
TEMP_FILE = "user_data.tmp"

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

user_data = {}
data_lock = threading.Lock()

# =========================
# DEFAULT USER STATE
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
        "caption_enabled": True,
        "selected_channels": [],
        "selected_thumb": None,
        "waiting_thumb": None,
        "thumb_action": None,
        "link_style": "video",   # video / number / circle / link
        "thumbs": {slot: None for slot in THUMB_SLOTS},
    }

# =========================
# SAVE / LOAD
# =========================
def save_data():
    try:
        with data_lock:
            serializable = {str(k): v for k, v in user_data.items()}

            with open(TEMP_FILE, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)

            if os.path.exists(DATA_FILE):
                shutil.copyfile(DATA_FILE, BACKUP_FILE)

            os.replace(TEMP_FILE, DATA_FILE)

    except Exception as e:
        logging.error(f"Save data error: {e}")


def load_data():
    global user_data

    def _load_from_file(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    raw = None

    try:
        if os.path.exists(DATA_FILE):
            raw = _load_from_file(DATA_FILE)
        elif os.path.exists(BACKUP_FILE):
            raw = _load_from_file(BACKUP_FILE)
        else:
            user_data = {}
            return

        fixed = {}
        for uid_str, value in raw.items():
            uid = int(uid_str)
            base = default_user_state()
            if isinstance(value, dict):
                base.update(value)

            if "thumbs" not in base or not isinstance(base["thumbs"], dict):
                base["thumbs"] = {slot: None for slot in THUMB_SLOTS}
            else:
                for slot in THUMB_SLOTS:
                    if slot not in base["thumbs"]:
                        base["thumbs"][slot] = None

            if "selected_channels" not in base or not isinstance(base["selected_channels"], list):
                base["selected_channels"] = []

            fixed[uid] = base

        user_data = fixed
        logging.info("User data loaded successfully")

    except Exception as e:
        logging.error(f"Load data error: {e}")
        user_data = {}

        try:
            if os.path.exists(BACKUP_FILE):
                raw = _load_from_file(BACKUP_FILE)
                fixed = {}
                for uid_str, value in raw.items():
                    uid = int(uid_str)
                    base = default_user_state()
                    if isinstance(value, dict):
                        base.update(value)
                    fixed[uid] = base
                user_data = fixed
                logging.info("Loaded from backup successfully")
        except Exception as e2:
            logging.error(f"Backup load failed: {e2}")
            user_data = {}

# =========================
# BASIC
# =========================
def is_admin(uid):
    return uid in ADMIN_IDS


def init_user(uid):
    if uid not in user_data:
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


def build_links(uid, links):
    links = unique_keep_order(links)
    if not links:
        return ""

    style = user_data[uid].get("link_style", "video")
    result = []

    for i, link in enumerate(links, 1):
        if style == "video":
            result.append(f"Video {i}\n{link}")
        elif style == "number":
            result.append(f"{i}) {link}")
        elif style == "circle":
            nums = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
            prefix = nums[i - 1] if i <= len(nums) else f"{i}."
            result.append(f"{prefix} {link}")
        elif style == "link":
            result.append(f"Link {i}\n{link}")
        else:
            result.append(f"Video {i}\n{link}")

    return "\n\n".join(result).strip()


def dedupe_text_lines(text):
    lines = [normalize_line(x) for x in (text or "").splitlines() if normalize_line(x)]
    return "\n".join(unique_keep_order(lines)).strip()


def is_header_like(line: str) -> bool:
    line = normalize_line(line)
    if not line:
        return True

    lower = line.lower()

    exact_keywords = [
        "join our channel",
        "watch video",
        "telegram channel",
        "whatsapp channel",
        "follow us",
        "subscribe",
    ]

    for word in exact_keywords:
        if word in lower:
            return True

    if lower.startswith("@") and len(line) < 40:
        return True

    if only_symbols_or_emoji(line):
        return True

    if len(re.findall(r"[🔥💥⚜️❤️✅🥰😍😘💎✨⭐🎉💯📢📌👉]", line)) >= 3 and len(line) < 70:
        return True

    promo_words = ["join", "telegram", "whatsapp", "follow", "subscribe"]
    if any(word in lower for word in promo_words) and len(line) < 100:
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
        "our channel",
        "കൂടുതൽ",
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
    cleaned = [line.rstrip() for line in (text or "").splitlines() if line.strip()]

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

    return unique_keep_order(result)


def arrange(uid, text):
    links = extract_links(text)
    if not links:
        return safe_text((text or "").strip())
    return safe_text(build_links(uid, links))


def text_edit(uid, text):
    mal_lines = clean_lines_keep_malayalam(uid, text)
    links = extract_links(text)

    parts = []
    if mal_lines:
        parts.append("\n".join(mal_lines).strip())

    if links:
        parts.append(build_links(uid, links))

    final = "\n\n".join([p for p in parts if p]).strip()
    if not final:
        final = (text or "").strip()

    return safe_text(dedupe_text_lines(final))


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
        for url in re.findall(r'https?://[^\s<>()"]+', line):
            if url not in links:
                links.append(url)

    main_text_lines = []
    ignore_patterns = [
        r"join",
        r"join our",
        r"telegram channel",
        r"whatsapp channel",
        r"follow",
        r"subscribe",
        r"watch video",
        r"video\s*\d+",
        r"^https?://",
        r"^\.$",
        r"^🆔$",
        r"കൂടുതൽ",
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

    links_block = build_links(uid, links)
    if links_block:
        result.append(links_block)

    return safe_text(dedupe_text_lines("\n\n".join(result).strip()))


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
            parts.append(build_links(uid, links))

        result = "\n\n".join(parts).strip()
        return safe_text(dedupe_text_lines(result if result else text))

    if user_data[uid]["text_edit_mode"]:
        return text_edit(uid, text)

    if user_data[uid]["arrange_mode"]:
        return arrange(uid, text)

    return safe_text(dedupe_text_lines(text.strip()))

# =========================
# SEND SAFE
# =========================
def send_message_safe(chat_id, text, reply_markup=None):
    try:
        return bot.send_message(chat_id, safe_text(text), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send message error to {chat_id}: {e}")


def send_photo_safe(chat_id, photo, caption="", reply_markup=None):
    try:
        return bot.send_photo(chat_id, photo, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send photo error to {chat_id}: {e}")


def send_video_safe(chat_id, video, caption="", reply_markup=None):
    try:
        return bot.send_video(chat_id, video, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send video error to {chat_id}: {e}")


def send_document_safe(chat_id, document, caption="", reply_markup=None):
    try:
        return bot.send_document(chat_id, document, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send document error to {chat_id}: {e}")


def send_animation_safe(chat_id, animation, caption="", reply_markup=None):
    try:
        return bot.send_animation(chat_id, animation, caption=safe_caption(caption), reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Send animation error to {chat_id}: {e}")

# =========================
# FORWARD HELPERS
# =========================
def report_forward_error(uid, channel_id, err):
    try:
        admin_text = f"⚠️ Forward failed\nChannel: {channel_id}\nError: {err}"
        send_message_safe(uid, admin_text, reply_markup=main_kb())
    except Exception as e:
        logging.error(f"Report forward error failed: {e}")


def forward_to_channels_text(uid, text):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            send_message_safe(ch, text)
        except Exception as e:
            logging.error(f"Forward text error to {ch}: {e}")
            report_forward_error(uid, ch, e)


def forward_to_channels_photo(uid, photo, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            send_photo_safe(ch, photo, caption=caption)
        except Exception as e:
            logging.error(f"Forward photo error to {ch}: {e}")
            report_forward_error(uid, ch, e)


def forward_to_channels_video(uid, video, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            send_video_safe(ch, video, caption=caption)
        except Exception as e:
            logging.error(f"Forward video error to {ch}: {e}")
            report_forward_error(uid, ch, e)


def forward_to_channels_document(uid, document, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            send_document_safe(ch, document, caption=caption)
        except Exception as e:
            logging.error(f"Forward document error to {ch}: {e}")
            report_forward_error(uid, ch, e)


def forward_to_channels_animation(uid, animation, caption=""):
    if not user_data[uid]["auto_forward"]:
        return

    for ch in user_data[uid]["selected_channels"]:
        try:
            send_animation_safe(ch, animation, caption=caption)
        except Exception as e:
            logging.error(f"Forward animation error to {ch}: {e}")
            report_forward_error(uid, ch, e)

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
    kb.row("🏷 Caption ON", "🚫 Caption OFF")
    kb.row("🔤 Link Style")
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


def link_style_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Video 1 Style", "1) Style")
    kb.row("① Style", "Link 1 Style")
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
        "🔥 VIP SMART FILTER BOT READY ✅\n\n"
        "• Thumb Change\n"
        "• Arrange Link\n"
        "• Keep Text + Links\n"
        "• Text Edit\n"
        "• Middle Text Mode\n"
        "• Header Remove\n"
        "• Footer Remove\n"
        "• Caption ON/OFF\n"
        "• Link Style Select\n"
        "• Auto Forward\n"
        "• Backup Save\n"
        "• Forward Error Report\n"
        "• Photo / Video / Document / Animation Support\n\n"
        "Buttons use ചെയ്യൂ 👇",
        reply_markup=main_kb()
    )

# =========================
# THUMB
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

    send_message_safe(m.chat.id, "ആദ്യം Set/Use Thumb ചെയ്യൂ", reply_markup=main_kb())


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
        send_message_safe(m.chat.id, "ആദ്യം thumb select ചെയ്യൂ ❌", reply_markup=main_kb())
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
    bot.reply_to(m, "Keep Text ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🧲 Keep Text OFF")
def keep_text_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["keep_text_mode"] = False
    save_data()
    bot.reply_to(m, "Keep Text OFF ❌")


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
    bot.reply_to(m, "Text Edit ON ✅")


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
    bot.reply_to(m, "Middle ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🎯 Middle OFF")
def middle_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return

    init_user(uid)
    user_data[uid]["middle_mode"] = False
    save_data()
    bot.reply_to(m, "Middle OFF ❌")


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


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🏷 Caption ON")
def caption_on(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["caption_enabled"] = True
    save_data()
    bot.reply_to(m, "Caption ON ✅")


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🚫 Caption OFF")
def caption_off(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["caption_enabled"] = False
    save_data()
    bot.reply_to(m, "Caption OFF ❌")

# =========================
# LINK STYLE
# =========================
@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "🔤 Link Style")
def choose_link_style(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    send_message_safe(m.chat.id, "Link style select ചെയ്യൂ 👇", reply_markup=link_style_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "Video 1 Style")
def link_style_video(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["link_style"] = "video"
    save_data()
    send_message_safe(m.chat.id, "Style set: Video 1 ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "1) Style")
def link_style_number(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["link_style"] = "number"
    save_data()
    send_message_safe(m.chat.id, "Style set: 1) ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "① Style")
def link_style_circle(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["link_style"] = "circle"
    save_data()
    send_message_safe(m.chat.id, "Style set: ① ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.content_type == "text" and m.text == "Link 1 Style")
def link_style_link(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    init_user(uid)
    user_data[uid]["link_style"] = "link"
    save_data()
    send_message_safe(m.chat.id, "Style set: Link 1 ✅", reply_markup=main_kb())

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
# AUTO FORWARD
# =========================
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

    style_map = {
        "video": "Video 1",
        "number": "1)",
        "circle": "①",
        "link": "Link 1"
    }

    text = (
        f"Thumb Mode: {'ON ✅' if user_data[uid]['thumb_mode'] else 'OFF ❌'}\n"
        f"Arrange Mode: {'ON ✅' if user_data[uid]['arrange_mode'] else 'OFF ❌'}\n"
        f"Keep Text Mode: {'ON ✅' if user_data[uid]['keep_text_mode'] else 'OFF ❌'}\n"
        f"Text Edit Mode: {'ON ✅' if user_data[uid]['text_edit_mode'] else 'OFF ❌'}\n"
        f"Middle Mode: {'ON ✅' if user_data[uid]['middle_mode'] else 'OFF ❌'}\n"
        f"Header Remove: {'ON ✅' if user_data[uid]['remove_header_mode'] else 'OFF ❌'}\n"
        f"Footer Remove: {'ON ✅' if user_data[uid]['remove_footer_mode'] else 'OFF ❌'}\n"
        f"Caption: {'ON ✅' if user_data[uid]['caption_enabled'] else 'OFF ❌'}\n"
        f"Auto Forward: {'ON ✅' if user_data[uid]['auto_forward'] else 'OFF ❌'}\n"
        f"Link Style: {style_map.get(user_data[uid]['link_style'], 'Video 1')}\n"
        f"Selected Thumb: {user_data[uid]['selected_thumb'] or 'None ❌'}\n\n"
        f"Selected Channels:\n{channel_text}"
    )

    send_message_safe(m.chat.id, text, reply_markup=main_kb())

# =========================
# PHOTO
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

        logging.info(f"Photo received from {uid}")

        if user_data[uid]["waiting_thumb"]:
            slot = user_data[uid]["waiting_thumb"]
            user_data[uid]["thumbs"][slot] = photo_id
            user_data[uid]["waiting_thumb"] = None
            user_data[uid]["thumb_action"] = None
            save_data()
            send_message_safe(m.chat.id, f"{slot} saved ✅", reply_markup=main_kb())
            return

        if user_data[uid]["thumb_mode"]:
            thumb = get_thumb(uid)
            send_photo_id = thumb if thumb else photo_id
            final_caption = caption.strip() if user_data[uid]["caption_enabled"] else ""
        else:
            send_photo_id = photo_id
            final_caption = apply_processing(uid, caption) if user_data[uid]["caption_enabled"] else ""

        send_photo_safe(m.chat.id, send_photo_id, caption=final_caption, reply_markup=main_kb())
        forward_to_channels_photo(uid, send_photo_id, final_caption)

    except Exception as e:
        logging.error(f"Photo handler error: {e}")
        send_message_safe(m.chat.id, "Photo process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())

# =========================
# VIDEO
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
        final_caption = apply_processing(uid, caption) if user_data[uid]["caption_enabled"] else ""

        logging.info(f"Video received from {uid}")

        send_video_safe(m.chat.id, video_id, caption=final_caption, reply_markup=main_kb())
        forward_to_channels_video(uid, video_id, final_caption)

    except Exception as e:
        logging.error(f"Video handler error: {e}")
        send_message_safe(m.chat.id, "Video process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())

# =========================
# DOCUMENT
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
        final_caption = apply_processing(uid, caption) if user_data[uid]["caption_enabled"] else ""

        logging.info(f"Document received from {uid}")

        send_document_safe(m.chat.id, doc_id, caption=final_caption, reply_markup=main_kb())
        forward_to_channels_document(uid, doc_id, final_caption)

    except Exception as e:
        logging.error(f"Document handler error: {e}")
        send_message_safe(m.chat.id, "Document process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())

# =========================
# ANIMATION
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
        final_caption = apply_processing(uid, caption) if user_data[uid]["caption_enabled"] else ""

        logging.info(f"Animation received from {uid}")

        send_animation_safe(m.chat.id, anim_id, caption=final_caption, reply_markup=main_kb())
        forward_to_channels_animation(uid, anim_id, final_caption)

    except Exception as e:
        logging.error(f"Animation handler error: {e}")
        send_message_safe(m.chat.id, "Animation process ചെയ്യാൻ പറ്റിയില്ല ❌", reply_markup=main_kb())

# =========================
# TEXT
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
        "🏷 Caption ON", "🚫 Caption OFF",
        "🔤 Link Style",
        "Video 1 Style", "1) Style", "① Style", "Link 1 Style",
        "📢 Select Channel",
        "🟢 Auto Forward ON", "🔴 Auto Forward OFF",
        "👁 Current Thumb", "📊 Current Settings",
        "Channel 1", "Channel 2", "Channel 3", "Channel 4", "Channel 5",
        "✅ Done", "🗑 Clear Channels", "⬅️ Back",
        "Photo 1", "Photo 2", "Photo 3", "Photo 4",
    }

    if m.text in ignore:
        return

    try:
        logging.info(f"Text received from {uid}")

        final_text = apply_processing(uid, m.text)

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
# RUN
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
