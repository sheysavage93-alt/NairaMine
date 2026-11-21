import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")
def keep_alive():
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()
import os
import sqlite3, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "")

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, ref_by INTEGER, last_mine INTEGER DEFAULT 0)")
conn.commit()

# fix old database if it doesn't have last_mine
try:
    cur.execute("ALTER TABLE users ADD COLUMN last_mine INTEGER DEFAULT 0")
    conn.commit()
except:
    pass

MINE_REWARD = 20
BRONZE_REWARD = 50
GOLD_REWARD = 75
MINE_COOLDOWN = 4 * 60 * 60  # 4 hours

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref_by = int(args[0]) if args and args[0].isdigit() else 0
    cur.execute("INSERT OR IGNORE INTO users (user_id, ref_by) VALUES (?, ?)", (user.id, ref_by))
    conn.commit()
    await update.message.reply_text(f"Welcome {user.first_name} to NairaMine! 💰\n\n⛏️ Use /mine to mine 20 Naira every 4 hours\n💰 Use /balance to check balance\n👥 Use /refer to get your link")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    bal = row[0] if row else 0
    await update.message.reply_text(f"Your balance: {bal} Naira")

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(f"Your referral link:\nhttps://t.me/{bot_username}?start={user_id}")

async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cur.execute("SELECT balance, last_mine FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, balance, last_mine) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        row = (0, 0)
    bal, last = row
    now = int(time.time())
    left = MINE_COOLDOWN - (now - last)
    if left > 0:
        hours = left // 3600
        mins = (left % 3600) // 60
        await update.message.reply_text(f"⛏️ You already mined!\nCome back in {hours}h {mins}m")
        return
    cur.execute("SELECT vip FROM users WHERE user_id=?", (user_id,))
    vip_row = cur.fetchone()
    vip_level = vip_row[0] if vip_row and vip_row[0] else "free"
    reward = BRONZE_REWARD if vip_level=="bronze" else GOLD_REWARD if vip_level=="gold" else MINE_REWARD
    new_bal = bal + reward
    cur.execute("UPDATE users SET balance=?, last_mine=? WHERE user_id=?", (new_bal, now, user_id))


async def vip(update, context):
    text = (
        "💎 VIP PLANS - LOCKED\n\n"
        "🆓 FREE - 120/day\n"
        "20 per mine, every 4 hours\n\n"
        "🥉 Bronze - ₦4,000\n"
        "50 per mine = 300/day for 15 days = ₦4,500\n\n"
        "🥇 Gold - ₦6,000\n"
        "75 per mine = 450/day for 15 days = ₦6,750\n\n"
        "Daily Tasks: 85/day extra\n"
        "Min Withdrawal: ₦3,000\n\n"
        "To buy, send payment and send screenshot to admin."
    )
    await update.message.reply_text(text)

async def tasks(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[InlineKeyboardButton("✅ Check-in +₦25", callback_data="checkin")],[InlineKeyboardButton("🎬 Watch Ads +₦40", callback_data="ads")],[InlineKeyboardButton("📢 Stay in Channel +₦20", callback_data="channel")],]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 DAILY TASKS - 85/day\n\nTap a button to claim:", reply_markup=reply_markup)
async def withdraw(update, context):
    user_id = update.effective_user.id
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    bal = row[0] if row else 0
    if bal < 3000:
        await update.message.reply_text(f"❌ Minimum withdrawal is ₦3,000.\nYour balance: ₦{bal}\nKeep mining!")
    else:
        await update.message.reply_text(f"✅ Withdrawal Request: ₦{bal}\n\nSend your Opay / Bank details to admin.\nYou can withdraw 1 time per 15-day round.")



async def do_checkin(update, context):
    import sqlite3, datetime
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    con2 = sqlite3.connect("users.db")
    cur2 = con2.cursor()
    cur2.execute("SELECT balance, last_checkin FROM users WHERE user_id=?", (user_id,))
    row = cur2.fetchone()
    today = datetime.date.today().isoformat()
    if row and len(row) > 1 and row[1] == today:
        await query.edit_message_text("❌ You already checked in today. Come back tomorrow!")
        con2.close()
        return
    bal = row[0] if row else 0
    new_bal = bal + 25
    cur2.execute("UPDATE users SET balance=?, last_checkin=? WHERE user_id=?", (new_bal, today, user_id))
    con2.commit(); con2.close()
    await query.edit_message_text(f"✅ Check-in Done! +₦25\nNew Balance: ₦{new_bal}")
async def do_ads(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    import datetime
    today = str(datetime.date.today())
    conn2 = sqlite3.connect('users.db')
    cur2 = conn2.cursor()
    cur2.execute("SELECT balance, last_ads FROM users WHERE user_id=?", (user_id,))
    row = cur2.fetchone()
    if not row:
        await query.edit_message_text("Send /start first!")
        conn2.close()
        return
    bal, last_ads = row
    if last_ads == today:
        await query.edit_message_text(f"❌ Ads already done today!\nBalance: ₦{bal}\nCome back tomorrow.")
        conn2.close()
        return
    new_bal = bal + 40
    cur2.execute("UPDATE users SET balance=?, last_ads=? WHERE user_id=?", (new_bal, today, user_id))
    conn2.commit()
    conn2.close()
    await query.edit_message_text(f"✅ Ads Watched! +₦40\nBalance: ₦{new_bal}")

async def do_channel(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    import datetime
    today = str(datetime.date.today())
    conn2 = sqlite3.connect('users.db')
    cur2 = conn2.cursor()
    cur2.execute("SELECT balance, last_channel FROM users WHERE user_id=?", (user_id,))
    row = cur2.fetchone()
    if not row:
        await query.edit_message_text("Send /start first!")
        conn2.close()
        return
    bal, last_channel = row
    if last_channel == today:
        await query.edit_message_text(f"❌ Channel task already done today!\nBalance: ₦{bal}\nCome back tomorrow.")
        conn2.close()
        return
    new_bal = bal + 20
    cur2.execute("UPDATE users SET balance=?, last_channel=? WHERE user_id=?", (new_bal, today, user_id))
    conn2.commit()
    conn2.close()
    await query.edit_message_text(f"✅ Channel Task Done! +₦20\nBalance: ₦{new_bal}")

def migrate():
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_ads TEXT DEFAULT ''")
    except: pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_channel TEXT DEFAULT ''")
    except: pass
    conn.commit()
    conn.close()

def main():
    migrate()


    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("mine", mine))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("withdraw", withdraw))
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(do_checkin, pattern="^checkin$"))
    app.add_handler(CallbackQueryHandler(do_ads, pattern="^ads$"))
    app.add_handler(CallbackQueryHandler(do_channel, pattern="^channel$"))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
