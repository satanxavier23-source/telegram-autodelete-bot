import os
import re
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Token ഇല്ല ❌")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# ====== STORAGE ======
replace_photo = None
waiting_photo = False

thumb_mode = False
link_mode = True
forward_mode = False

selected_channels = set()

# ====== CHANNEL IDs ======
CHANNELS = {
    "Channel 1": -1002674664027,
    "Channel 2": -1002514181198,
    "Channel 3": -1002427180742
}

# ====== FUNCTIONS ======
def extract_links(text):
    if not text:
        return []
    return re.findall(r'https?://\S+', text)

def arrange_links(text):
    links = extract_links(text)
    if not links:
        return None

    result = "FULL VIDEO 👀🌸\n\n"
    for i, link in enumerate(links, 1):
        result += f"VIDEO {i} ⤵️\n{link}\n\n"
    return result.strip()

def main_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 Set Photo", callback_data="set_photo")
    )
    markup.add(
        types.InlineKeyboardButton("🟢 Thumb ON", callback_data="thumb_on"),
        types.InlineKeyboardButton("🔴 Thumb OFF", callback_data="thumb_off")
    )
    markup.add(
        types.InlineKeyboardButton("🟢 Link ON", callback_data="link_on"),
        types.InlineKeyboardButton("🔴 Link OFF", callback_data="link_off")
    )
    markup.add(
        types.InlineKeyboardButton("🟢 Forward ON", callback_data="forward_on"),
        types.InlineKeyboardButton("🔴 Forward OFF", callback_data="forward_off")
    )
    markup.add(
        types.InlineKeyboardButton("📢 Select Channels", callback_data="select_channels")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Status", callback_data="status")
    )
    return markup

def channel_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Channel 1", callback_data="ch_1"),
        types.InlineKeyboardButton("Channel 2", callback_data="ch_2")
    )
    markup.add(
        types.InlineKeyboardButton("Channel 3", callback_data="ch_3")
    )
    markup.add(
        types.InlineKeyboardButton("🗑 Clear Channels", callback_data="clear_channels")
    )
    markup.add(
        types.InlineKeyboardButton("⬅ Back", callback_data="back_main")
    )
    return markup

def get_status_text():
    return (
        f"📊 Bot Status\n\n"
        f"Thumb: {'ON ✅' if thumb_mode else 'OFF ❌'}\n"
        f"Link Arrange: {'ON ✅' if link_mode else 'OFF ❌'}\n"
        f"Auto Forward: {'ON ✅' if forward_mode else 'OFF ❌'}\n"
        f"Saved Photo: {'Yes ✅' if replace_photo else 'No ❌'}\n"
        f"Selected Channels: {len(selected_channels)}"
    )

# ====== START ======
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "🔥 Inline UI Bot Ready 🔥\n\n"
        "താഴെയുള്ള buttons use ചെയ്യൂ.",
        reply_markup=main_inline_keyboard()
    )

# ====== CALLBACK HANDLER ======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global waiting_photo, thumb_mode, link_mode, forward_mode

    data = call.data

    if data == "set_photo":
        waiting_photo = True
        bot.answer_callback_query(call.id, "Photo അയക്കൂ 📸")
        bot.send_message(call.message.chat.id, "Replacement photo അയക്കൂ 📸")
        return

    elif data == "thumb_on":
        if not replace_photo:
            bot.answer_callback_query(call.id, "Photo set ചെയ്തിട്ടില്ല ❌")
            return
        thumb_mode = True
        bot.answer_callback_query(call.id, "Thumb ON ✅")

    elif data == "thumb_off":
        thumb_mode = False
        bot.answer_callback_query(call.id, "Thumb OFF ❌")

    elif data == "link_on":
        link_mode = True
        bot.answer_callback_query(call.id, "Link Arrange ON ✅")

    elif data == "link_off":
        link_mode = False
        bot.answer_callback_query(call.id, "Link Arrange OFF ❌")

    elif data == "forward_on":
        forward_mode = True
        bot.answer_callback_query(call.id, "Auto Forward ON 🚀")

    elif data == "forward_off":
        forward_mode = False
        bot.answer_callback_query(call.id, "Auto Forward OFF ❌")

    elif data == "select_channels":
        bot.edit_message_text(
            "📢 Channels select ചെയ്യൂ",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=channel_inline_keyboard()
        )
        return

    elif data == "status":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, get_status_text(), reply_markup=main_inline_keyboard())
        return

    elif data == "ch_1":
        selected_channels.add(CHANNELS["Channel 1"])
        bot.answer_callback_query(call.id, "Channel 1 added ✅")

    elif data == "ch_2":
        selected_channels.add(CHANNELS["Channel 2"])
        bot.answer_callback_query(call.id, "Channel 2 added ✅")

    elif data == "ch_3":
        selected_channels.add(CHANNELS["Channel 3"])
        bot.answer_callback_query(call.id, "Channel 3 added ✅")

    elif data == "clear_channels":
        selected_channels.clear()
        bot.answer_callback_query(call.id, "Channels cleared ❌")

    elif data == "back_main":
        bot.edit_message_text(
            "🔥 Main Menu 🔥",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard()
        )
        return

# ====== PHOTO HANDLER ======
@bot.message_handler(content_types=['photo'])
def photo_handler(msg):
    global replace_photo, waiting_photo

    if waiting_photo:
        replace_photo = msg.photo[-1].file_id
        waiting_photo = False
        bot.reply_to(msg, "Photo saved ✅", reply_markup=main_inline_keyboard())
        return

    caption = msg.caption or ""

    if thumb_mode and replace_photo:
        photo_id = replace_photo
    else:
        photo_id = msg.photo[-1].file_id

    if link_mode:
        final_caption = arrange_links(caption) or "Links ഇല്ല ❌"
    else:
        final_caption = caption

    bot.send_photo(msg.chat.id, photo_id, caption=final_caption)

    if forward_mode and selected_channels:
        for ch in selected_channels:
            try:
                bot.send_photo(ch, photo_id, caption=final_caption)
            except Exception as e:
                print("Forward error:", e)

print("Bot running 🔥")
bot.infinity_polling(skip_pending=True)
