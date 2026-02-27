import os
import sqlite3
import threading
import time
import asyncio
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

# -------------------- Load Environment Variables --------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
if PRIVATE_CHANNEL_ID and PRIVATE_CHANNEL_ID.lstrip("-").isdigit():
    PRIVATE_CHANNEL_ID = int(PRIVATE_CHANNEL_ID)

ADMIN_IDS = []
_admins = os.getenv("ADMIN_IDS", "")
if _admins:
    for x in _admins.split(","):
        x = x.strip()
        if x and x.isdigit():
            ADMIN_IDS.append(int(x))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")
if not PRIVATE_CHANNEL_ID:
    raise RuntimeError("PRIVATE_CHANNEL_ID is required")

# -------------------- Database Setup --------------------
DB_PATH = "subscriptions.db"
db_lock = threading.Lock()

def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
                        user_id INTEGER PRIMARY KEY,
                        expiry_date INTEGER NOT NULL)''')
        conn.commit()
        conn.close()

def add_subscription(user_id, days):
    expiry = int(time.time()) + days * 86400
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("REPLACE INTO subscriptions (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry))
        conn.commit()
        conn.close()

def remove_subscription(user_id):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

def get_expired_users(now=None):
    if now is None:
        now = int(time.time())
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id FROM subscriptions WHERE expiry_date <= ?", (now,))
        expired = [row[0] for row in c.fetchall()]
        conn.close()
    return expired

def get_subscription_expiry(user_id):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT expiry_date FROM subscriptions WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

init_db()

# -------------------- Flask App --------------------
app = Flask(__name__)

# -------------------- Bot Setup --------------------
application = Application.builder().token(BOT_TOKEN).build()

# -------------------- Premium Constants --------------------
TELEBIRR_ACCOUNT = "0987973732"
PRICE_1 = 700
PRICE_2 = 1400
PRICE_3 = 2000

def format_expiry(timestamp):
    if not timestamp:
        return "`Not subscribed`"
    dt = datetime.fromtimestamp(timestamp)
    return f"`{dt.strftime('%Y-%m-%d %H:%M:%S')}`"

def plan_keyboard():
    keyboard = [
        [InlineKeyboardButton(f"💎 1 Month – {PRICE_1} Birr", callback_data="plan:1")],
        [InlineKeyboardButton(f"✨ 2 Months – {PRICE_2} Birr", callback_data="plan:2")],
        [InlineKeyboardButton(f"🔥 3 Months – {PRICE_3} Birr", callback_data="plan:3")],
    ]
    return InlineKeyboardMarkup(keyboard)

def proceed_keyboard():
    keyboard = [[InlineKeyboardButton("💳 Proceed to Membership", callback_data="proceed")]]
    return InlineKeyboardMarkup(keyboard)

# -------------------- Premium Welcome Message --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "╔══════════════════════════════╗\n"
        "     👑🔥 **VVIP HABESHA** 🔥👑     \n"
        "╚══════════════════════════════╝\n\n"
        "✨ *Welcome to the most exclusive Habesha premium channel!* ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 **What you'll enjoy:**\n"
        "• 🔥 Exclusive hot videos & photos\n"
        "• 📅 Daily premium content updates\n"
        "• 🎥🔴 Live streaming every night\n"
        "• 💃🏾 Sexy live performances\n"
        "• 💬 Direct interaction with the community\n"
        "• 🕒 24/7 VIP support\n\n"
        "🇪🇹 **ምን ያገኛሉ:**\n"
        "• 🔥 ልዩ ሙቅ ቪዲዮዎች እና ፎቶዎች\n"
        "• 📅 ዕለታዊ አዲስ ፕሪሚየም ኮንቴንት\n"
        "• 🔴 በየምሽቱ ቀጥታ ስርጭት\n"
        "• 💃🏾 ሴክሲ የቀጥታ ትዕይንቶች\n"
        "• 💬 ቀጥተኛ ውይይት በፕራይቬት ቻናል\n"
        "• 🕒 24/7 ድጋፍ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 *Choose your membership plan below* 👇"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=proceed_keyboard())

# -------------------- Premium Proceed Callback --------------------
async def proceed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "🌟 **Select your VIP plan** 🌟\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 **1 Month** – Full access for 30 days\n"
        "✨ **2 Months** – Save more with longer access\n"
        "🔥 **3 Months** – Best value, ultimate experience\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap a button below to continue:"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=plan_keyboard())

# -------------------- Premium Plan Selection --------------------
async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    if data[0] != "plan":
        return
    months = int(data[1])
    context.user_data['selected_months'] = months
    price = {1: PRICE_1, 2: PRICE_2, 3: PRICE_3}[months]

    text = (
        f"✅ **You selected {months} month(s)**\n"
        f"💵 **Total: {price} Birr**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🇺🇸 *Please send exactly **{price} Birr** to the following Telebirr account:*\n"
        f"`{TELEBIRR_ACCOUNT}`\n\n"
        "📸 *After payment, send a screenshot of the transaction.*\n\n"
        f"🇪🇹 *እባክዎ በትክክል **{price} ብር** ወደዚህ ቴሌብር አካውንት ይላኩ።*\n"
        f"`{TELEBIRR_ACCOUNT}`\n\n"
        "*ከክፍያ በኋላ የስክሪን ሾት ይላኩ።*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await query.edit_message_text(text, parse_mode="Markdown")

# -------------------- Premium Photo Handler --------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    months = context.user_data.get('selected_months')
    if not months:
        await update.message.reply_text(
            "⚠️ Please first choose a subscription plan using /start.\n\n"
            "👉 Tap the button below to begin.",
            reply_markup=proceed_keyboard()
        )
        return

    price = {1: PRICE_1, 2: PRICE_2, 3: PRICE_3}[months]
    photo = update.message.photo[-1]
    caption = (
        "╔════════════════════════╗\n"
        "   💳 **NEW PAYMENT** 💳   \n"
        "╚════════════════════════╝\n\n"
        f"👤 *From:* [{user.first_name}](tg://user?id={user.id})\n"
        f"🆔 *User ID:* `{user.id}`\n"
        f"📛 *Username:* @{user.username or 'N/A'}\n"
        f"📅 *Plan:* {months} month(s)\n"
        f"💰 *Amount:* {price} Birr\n"
        f"🏦 *Telebirr:* `{TELEBIRR_ACCOUNT}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Approve or decline below* 👇"
    )
    keyboard = [
        [
            InlineKeyboardButton(f"✅ Approve ({months} months)", callback_data=f"approve:{user.id}:{months}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline:{user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")

    await update.message.reply_text(
        "✅ **Your payment proof has been forwarded to our admins.**\n"
        "⏳ You'll receive a notification once it's approved.\n\n"
        "✅ **የክፍያ ማረጋገጫዎ ለአስተዳዳሪዎቻችን ተልኳል።**\n"
        "⏳ ሲፀድቅ ይነገርዎታል።"
    )
    context.user_data.clear()

# -------------------- Premium Callback Handler --------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.")
        return

    data = query.data.split(":")
    action = data[0]
    user_id = int(data[1])

    if action == "approve":
        months = int(data[2])
        add_subscription(user_id, months * 30)
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=PRIVATE_CHANNEL_ID,
                member_limit=1,
                expire_date=int(time.time()) + months * 30 * 86400
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "╔══════════════════════════════════╗\n"
                    "   🎉 **PAYMENT APPROVED!** 🎉   \n"
                    "╚══════════════════════════════════╝\n\n"
                    f"✨ **You have been granted access for {months} month(s).** ✨\n\n"
                    f"🔗 **Your exclusive invite link:**\n{invite_link.invite_link}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ *This link expires in {months} months and can only be used once.*\n\n"
                    "🇪🇹 ክፍያዎ ጸድቋል! የመግቢያ ሊንክዎ ከላይ አለ።\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                text=f"✅ **Approved user `{user_id}` for {months} months.**\n\n📨 Invite link sent.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Approval failed: {e}")
    elif action == "decline":
        await query.edit_message_text(f"❌ **Declined user `{user_id}`.**", parse_mode="Markdown")

# -------------------- Other Handlers (Help, Status, Renew, Approve, List) --------------------
# (These remain largely the same but with enhanced formatting)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **VVIP Habesha Bot Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 **For everyone:**\n"
        "/start – 🚀 Begin your premium journey\n"
        "/help – ℹ️ Show this help\n"
        "/status – 📊 Check your subscription status\n"
        "/renew – 🔄 Request renewal\n\n"
        "👑 **For admins only:**\n"
        "/approve `<user_id>` [months] – ✅ Manually approve (default 1 month)\n"
        "/list – 📋 List all active subscribers\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expiry = get_subscription_expiry(user_id)
    if expiry and expiry > int(time.time()):
        remaining = expiry - int(time.time())
        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        status_text = (
            "✅ **You are an active VIP member!**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **Expires:** {format_expiry(expiry)}\n"
            f"⏳ **Time left:** {days} days, {hours} hours\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    elif expiry:
        status_text = (
            "❌ **Your membership has expired.**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **Expired on:** {format_expiry(expiry)}\n"
            "Use /renew to request a renewal.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        status_text = (
            "❌ **You are not subscribed.**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Send /start to choose a plan and join the VIP experience!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def renew_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    "🔄 **Renewal Request**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 *From:* [{user.first_name}](tg://user?id={user.id})\n"
                    f"🆔 *User ID:* `{user.id}`\n"
                    f"📛 *Username:* @{user.username or 'N/A'}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")
    await update.message.reply_text(
        "📩 **Your renewal request has been sent to the admins.**\n\n"
        "📩 **የእድሳት ጥያቄዎ ለአስተዳዳሪዎች ተልኳል።**"
    )

async def approve_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /approve <user_id> [months]")
        return
    try:
        user_id = int(context.args[0])
        months = int(context.args[1]) if len(context.args) > 1 else 1
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return

    add_subscription(user_id, months * 30)
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            member_limit=1,
            expire_date=int(time.time()) + months * 30 * 86400
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "╔══════════════════════════════════╗\n"
                "   🎉 **MANUAL APPROVAL** 🎉   \n"
                "╚══════════════════════════════════╝\n\n"
                f"✨ **An admin has granted you access for {months} month(s).** ✨\n\n"
                f"🔗 **Your exclusive invite link:**\n{invite_link.invite_link}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ **Approved user `{user_id}` for {months} months.**", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Approval failed: {e}")

async def list_subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    now = int(time.time())
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, expiry_date FROM subscriptions ORDER BY expiry_date")
        rows = c.fetchall()
        conn.close()
    if not rows:
        await update.message.reply_text("📭 **No active subscribers.**", parse_mode="Markdown")
        return
    lines = ["📋 **Active Subscribers:**\n━━━━━━━━━━━━━━━━━━━━━━━━━"]
    for uid, exp in rows:
        status = "✅" if exp > now else "❌"
        lines.append(f"{status} `{uid}` – expires {format_expiry(exp)}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

def auto_cleanup():
    while True:
        time.sleep(86400)
        now = int(time.time())
        expired = get_expired_users(now)
        if expired:
            print(f"🧹 Cleaning up {len(expired)} expired users...")
            for user_id in expired:
                try:
                    asyncio.run(application.bot.ban_chat_member(
                        chat_id=PRIVATE_CHANNEL_ID,
                        user_id=user_id
                    ))
                    remove_subscription(user_id)
                    asyncio.run(application.bot.send_message(
                        chat_id=user_id,
                        text="❌ Your subscription has expired. To renew, please send a new payment screenshot."
                    ))
                    print(f"✅ Removed expired user {user_id}")
                except Exception as e:
                    print(f"❌ Error cleaning up user {user_id}: {e}")
        else:
            print("🧹 No expired users found.")

# -------------------- Add Handlers to Application --------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("status", status_command))
application.add_handler(CommandHandler("renew", renew_request))
application.add_handler(CommandHandler("approve", approve_manual, filters=filters.User(user_id=ADMIN_IDS)))
application.add_handler(CommandHandler("list", list_subscribers, filters=filters.User(user_id=ADMIN_IDS)))
application.add_handler(CallbackQueryHandler(proceed_callback, pattern="^proceed$"))
application.add_handler(CallbackQueryHandler(plan_callback, pattern="^plan:"))
application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(approve|decline):"))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# -------------------- Initialize Application --------------------
async def init_app():
    await application.initialize()
asyncio.run(init_app())

# -------------------- Flask Routes --------------------
@app.route("/")
def health():
    return "Bot is running (webhook mode)", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates."""
    print("✅ Webhook received.")
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        print(f"✅ Update {update.update_id} processed.")
        return "OK", 200
    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        return "OK", 200

@app.route("/set_webhook")
def set_webhook():
    """Register the webhook with Telegram using a temporary bot."""
    try:
        public_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url.rstrip('/'))
        if public_url.startswith('http://'):
            public_url = public_url.replace('http://', 'https://', 1)
        webhook_url = f"{public_url}/webhook"

        from telegram import Bot
        temp_bot = Bot(token=BOT_TOKEN)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(temp_bot.set_webhook(url=webhook_url))
        loop.close()
        return f"✅ Webhook set to {webhook_url}"
    except Exception as e:
        return f"❌ Error: {e}", 500

# -------------------- Run Flask --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)