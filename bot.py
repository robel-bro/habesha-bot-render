import os
import sqlite3
import threading
import time
import asyncio
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
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
# Build the application without any updater (polling is completely disabled)
application = Application.builder().token(BOT_TOKEN).build()

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
        [InlineKeyboardButton(f"1 Month – {PRICE_1} Birr", callback_data="plan:1")],
        [InlineKeyboardButton(f"2 Months – {PRICE_2} Birr", callback_data="plan:2")],
        [InlineKeyboardButton(f"3 Months – {PRICE_3} Birr", callback_data="plan:3")],
    ]
    return InlineKeyboardMarkup(keyboard)

def proceed_keyboard():
    keyboard = [[InlineKeyboardButton("✅ Proceed to Membership", callback_data="proceed")]]
    return InlineKeyboardMarkup(keyboard)

# -------------------- Telegram Bot Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with channel benefits and a 'Proceed' button."""
    welcome_text = (
        "👋🔥 Welcome to Habesha Wesib Official Premium Channel! 🔥💋\n\n"
        "Get ready for an exclusive adult entertainment experience designed just for you 😍✨ We proudly deliver premium content every single day for our valued members 💎📅\n\n"
        "✨💎 What You’ll Enjoy:\n"
        "• 🔥 Exclusive hot videos and photos 📸🎥\n"
        "• 📅 Daily premium updates\n"
        "• 🎥🔴 Live streaming sessions every night 🌙🔥\n"
        "• 💃🏾 Sexy live performances & private shows 😍\n"
        "• 💬 Direct interaction with our private community\n"
        "• 🕒 24/7 support\n\n"
        "Join our 🔴 LIVE sessions every night 🌙 to watch the most beautiful Habesha girls 💃🏾🔥, interact with them directly in the chat 💬❤️, and enjoy an unforgettable premium experience 😍✨\n\n"
        "Don’t just watch 👀 — be an active participant 💬🔥 and elevate your experience to the next level 🚀💎\n\n"
        "👇👇 Press the button below to choose your membership plan and proceed 💳✅\n\n"
        "🔥🇪🇹 እንኳን ወደ ሐበሻ ወሲብ ኦፊሻል ፕሪሚየም ቻናል በደህና መጡ! 🔥💋\n\n"
        "ለእርስዎ ብቻ የተዘጋጀ ልዩ የወሲብ መዝናኛ ተሞክሮ ይጠብቃችኋል 😍✨ በየቀኑ ፕሪሚየም ኮንቴንት እናቀርባለን 📅💎\n\n"
        "✨💎 የምታገኙት:\n"
        "• 🔥 ልዩ ሙቅ ቪዲዮዎች እና ፎቶዎች 📸🎥\n"
        "• 📅 ዕለታዊ አዲስ ፕሪሚየም ኮንቴንት\n"
        "• 🔴 በየምሽቱ ቀጥታ (Live) ስርጭት 🌙🎥\n"
        "• 💃🏾 ሴክሲ የቀጥታ ትዕይንቶች 😍🔥\n"
        "• 💬 በፕራይቬት ቻናላችን ውስጥ ቀጥተኛ መሳተፍ\n"
        "• 🕒 24/7 ድጋፍ\n\n"
        "በLive 🔴 ተገኝታችሁ ቆንጆ የሀበሻ ሴቶችን 💃🏾🔥 ይመልከቱ፣ በቻት 💬 ቀጥታ ይነጋገሩ እና ልዩ ተሞክሮ ይደሰቱ 😍✨\n\n"
        "ብቻ ተመልካች አትሁኑ 👀 — ንቁ ተሳታፊ በመሆን ይደሰቱ 💬🔥\n\n"
        "👇👇 የአባልነት ፕላንዎን ለመምረጥ ከታች ያለውን ቁልፍ ይጫኑ"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=proceed_keyboard())

async def proceed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please select your membership plan:",
        reply_markup=plan_keyboard()
    )

async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    if data[0] != "plan":
        return
    months = int(data[1])
    context.user_data['selected_months'] = months

    price = {1: PRICE_1, 2: PRICE_2, 3: PRICE_3}.get(months, PRICE_1)

    confirm_text = (
        f"✅ *You selected {months} month(s) – Total: {price} Birr*\n\n"
        f"🇺🇸 Please send **{price} Birr** to the following Telebirr account:\n"
        f"`{TELEBIRR_ACCOUNT}`\n\n"
        f"After payment, **send a screenshot** of the transaction.\n\n"
        f"🇪🇹 እባክዎ **{price} ብር** ወደዚህ ቴሌብር አካውንት ይላኩ።\n"
        f"`{TELEBIRR_ACCOUNT}`\n\n"
        f"ከክፍያ በኋላ የስክሪን ሾት ይላኩ።"
    )
    await query.edit_message_text(confirm_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    months = context.user_data.get('selected_months')
    if not months:
        await update.message.reply_text(
            "🇺🇸 Please first choose a subscription plan using /start.\n"
            "🇪🇹 እባክዎ መጀመሪያ የደንበኝነት ምርጫዎን ይምረጡ።",
            reply_markup=proceed_keyboard()
        )
        return

    price = {1: PRICE_1, 2: PRICE_2, 3: PRICE_3}.get(months, PRICE_1)

    photo = update.message.photo[-1]
    caption = (
        f"💳 *New payment screenshot*\n"
        f"From: [{user.first_name}](tg://user?id={user.id})\n"
        f"User ID: `{user.id}`\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Plan: {months} month(s) – {price} Birr\n"
        f"Telebirr account: `{TELEBIRR_ACCOUNT}`"
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
        "✅ Your screenshot has been sent. You'll be notified once approved.\n\n"
        "✅ የስክሪን ሾትዎ ተልኳል። ሲፀድቅ ይነገርዎታል።"
    )
    context.user_data.clear()

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
                    f"🎉 *Your payment has been approved! / ክፍያዎ ጸድቋል!*\n\n"
                    f"🇺🇸 You have been granted access for {months} month(s).\n"
                    f"Here is your invite link:\n{invite_link.invite_link}\n\n"
                    f"🇪🇹 የ{months} ወር መዳረሻ ተሰጥቶዎታል።\n"
                    f"የመግቢያ ሊንክዎ ይህ ነው።"
                ),
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                text=f"✅ Approved user `{user_id}` for {months} months.\n\nInvite link sent.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Approval failed: {e}")
    elif action == "decline":
        await query.edit_message_text(f"❌ Declined user `{user_id}`.", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display available commands and usage."""
    help_text = (
        "📌 *Available Commands*\n"
        "/start - Begin interaction and choose membership plan\n"
        "/status - Check your subscription expiry\n"
        "/renew - Request a subscription renewal approval\n"
        "/help - Show this help message\n"
        "\n"
        "🛠 *Admin Commands* (admins only)\n"
        "/approve <user_id> <months> - Manually approve a user\n"
        "/list - List all subscribers and expiry dates\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the user their current subscription status."""
    user_id = update.effective_user.id
    expiry = get_subscription_expiry(user_id)
    now = int(time.time())
    if not expiry or expiry <= now:
        await update.message.reply_text(
            "🇺🇸 You are not currently subscribed or your subscription has expired.\n"
            "Use /start to choose a plan.\n"
            "\n🇪🇹 የእርስዎ የደንበኝነት ጊዜ ያልተሠራ ነው ወይም የጨረሰ ነው።\n"
            "/start ን በመጠቀም ፕላን ይምረጡ።",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"✅ Your subscription expires on {format_expiry(expiry)}\n"
            "Use /renew to request more time.",
            parse_mode="Markdown"
        )

async def renew_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward a renewal request to admins."""
    user = update.effective_user
    expiry = get_subscription_expiry(user.id)
    expiry_text = format_expiry(expiry)
    msg = (
        f"🔔 Renewal request from [{user.first_name}](tg://user?id={user.id}) ``{user.id}``\n"
        f"Current expiry: {expiry_text}\n"
        "Use /approve <user_id> <months> to grant additional time."
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")
    await update.message.reply_text(
        "✅ Your renewal request has been sent to the admins.\n"
        "🔁 They will respond once a decision is made."
    )

async def approve_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually approve a subscription."""
    args = context.args
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text(
            "Usage: /approve <user_id> <months>\n" 
            "Example: /approve 123456789 1"
        )
        return
    user_id = int(args[0])
    months = int(args[1])
    add_subscription(user_id, months * 30)
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            member_limit=1,
            expire_date=int(time.time()) + months * 30 * 86400,
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 *Your subscription has been approved!*\n"
                f"You have been granted access for {months} month(s).\n"
                f"Here is your invite link:\n{invite_link.invite_link}"
            ),
            parse_mode="Markdown",
        )
        await update.message.reply_text(f"✅ Approved {user_id} for {months} months. Invite link sent.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send invite link: {e}")

async def list_subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to show all subscribers and expiries."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, expiry_date FROM subscriptions ORDER BY expiry_date DESC")
        rows = c.fetchall()
        conn.close()
    if not rows:
        await update.message.reply_text("No subscribers found.")
        return
    lines = []
    now = int(time.time())
    for uid, exp in rows:
        status = "(expired)" if exp <= now else ""
        lines.append(f"`{uid}` – {format_expiry(exp)} {status}")
    text = "\n".join(lines)
    # Telegram limits message size; split if too long
    for chunk in [text[i:i+3900] for i in range(0, len(text), 3900)]:
        await update.message.reply_text(chunk, parse_mode="Markdown")

# -------------------- Add Handlers to Application --------------------

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

# --- Initialize the application (no polling!) ---
async def init_app():
    await application.initialize()
    # We do NOT call start() here. For pure webhook mode, initialize() is enough.
asyncio.run(init_app())

# -------------------- Flask Routes --------------------
@app.route("/")
def health():
    return "Bot is running (webhook mode)", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates."""
    print("✅ Webhook endpoint hit.")
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        # Process the update in a new event loop to avoid conflicts
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
    """Register the webhook with Telegram."""
    try:
        # Use Render's public URL
        public_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url.rstrip('/'))
        if public_url.startswith('http://'):
            public_url = public_url.replace('http://', 'https://', 1)
        webhook_url = f"{public_url}/webhook"

        # Use a temporary bot to avoid connection pool issues
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