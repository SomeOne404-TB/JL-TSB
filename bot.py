import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# 🔒 استخدام متغيرات البيئة
BOT_TOKEN = os.getenv('BOT_TOKEN', "8268539876:AAHgjRRb-mF3u2lVTzA7VR76dv4KBmObjrk")
OWNER_ID = int(os.getenv('OWNER_ID', "1484010221"))

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔧 تعديل مسار قاعدة البيانات للعمل على Render
def get_db_path():
    return '/tmp/user_data.db'

# إعداد قاعدة البيانات
def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # جدول بيانات المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT,
            user_id TEXT UNIQUE NOT NULL,
            location TEXT,
            more_info TEXT,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المستخدمين المعتمدين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS approved_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            approved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # جدول طلبات الانضمام
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS join_requests (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # جدول المستخدمين المحظورين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            banned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            banned_by INTEGER,
            reason TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# إضافة المالك تلقائياً كمستخدم معتمد
def add_owner_to_approved():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT OR IGNORE INTO approved_users (user_id, username, first_name, status) VALUES (?, ?, ?, ?)',
            (OWNER_ID, 'owner', 'Bot Owner', 'owner')
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()

# التحقق من صلاحية المستخدم
def is_approved_user(user_id):
    if user_id == OWNER_ID:
        return True
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM approved_users WHERE user_id = ? AND status = "active"', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# التحقق من وجود بيانات مكررة
def is_duplicate_data(user_id):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users_data WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# التحقق إذا كان المستخدم محظوراً
def is_banned_user(user_id):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM banned_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name

    # التحقق إذا كان المستخدم محظوراً
    if is_banned_user(user_id):
        await update.message.reply_text(
            "🚫 **Access Denied**\n\n"
            "You have been banned from using this bot.\n"
            "Contact the bot owner for more information."
        )
        return

    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("➕ Add New Data", callback_data="add_data")],
            [InlineKeyboardButton("📋 View Pending Requests", callback_data="view_requests")],
            [InlineKeyboardButton("👥 Manage Approved Users", callback_data="manage_users")],
            [InlineKeyboardButton("🔍 Search User Data", callback_data="search_data")],
            [InlineKeyboardButton("📊 Database Stats", callback_data="db_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👑 **Owner Panel**\n\n"
            "Welcome back, Owner! Choose an option:",
            reply_markup=reply_markup
        )
        return

    if is_approved_user(user_id):
        keyboard = [
            [InlineKeyboardButton("🔍 Search User Data", callback_data="search_data")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔍 **User Data Search Bot**\n\n"
            "Welcome! Use the button below to search for user data:",
            reply_markup=reply_markup
        )
    else:
        # إرسال طلب الانضمام للمالك
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO join_requests (user_id, username, first_name, status) VALUES (?, ?, ?, ?)',
                (user_id, username, first_name, 'pending')
            )
            conn.commit()
            
            # إرسال إشعار للمالك
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🆕 **New Join Request**\n\n"
                     f"👤 User: {first_name}\n"
                     f"📱 Username: @{username}\n"
                     f"🆔 ID: `{user_id}`",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            await update.message.reply_text(
                "📨 **Request Sent**\n\n"
                "Your request has been sent to the bot owner. Please wait for approval.\n"
                "You will be notified once your request is processed."
            )
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again later.")
        finally:
            conn.close()

# معالجة أزرار القائمة
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "add_data":
        if user_id == OWNER_ID:
            await query.edit_message_text(
                "📝 **Add New User Data**\n\n"
                "Please send user data in the following format:\n\n"
                "`Name: John Doe\n"
                "Username: @johndoe\n"
                "User ID: 123456789\n"
                "Location: New York, USA\n"
                "More Info: Additional details about the user`\n\n"
                "**Required fields:** Name, User ID\n"
                "**Optional fields:** Username, Location, More Info\n\n"
                "Each field should be on a separate line.",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_data'] = True
    
    elif data == "view_requests":
        if user_id == OWNER_ID:
            await show_pending_requests(query, context)
    
    elif data == "manage_users":
        if user_id == OWNER_ID:
            await show_approved_users(query, context)
    
    elif data == "search_data":
        if is_approved_user(user_id):
            await query.edit_message_text(
                "🔍 **Search User Data**\n\n"
                "Please send any search term (name, username, user ID, location, or more info):"
            )
            context.user_data['searching'] = True
    
    elif data == "db_stats":
        if user_id == OWNER_ID:
            await show_database_stats(query, context)
    
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id == OWNER_ID:
            await handle_request_decision(query, context, data)
    
    elif data.startswith("ban_") or data.startswith("unban_") or data.startswith("view_banned_"):
        if user_id == OWNER_ID:
            await handle_user_management(query, context, data)

# عرض إحصائيات قاعدة البيانات
async def show_database_stats(query, context):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # إحصائيات بيانات المستخدمين
    cursor.execute('SELECT COUNT(*) FROM users_data')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM approved_users WHERE status = "active"')
    total_approved = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM join_requests WHERE status = "pending"')
    pending_requests = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM banned_users')
    banned_users = cursor.fetchone()[0]
    
    conn.close()
    
    text = (
        "📊 **Database Statistics**\n\n"
        f"👥 **Total Users in Database:** {total_users}\n"
        f"✅ **Active Approved Users:** {total_approved}\n"
        f"⏳ **Pending Requests:** {pending_requests}\n"
        f"🚫 **Banned Users:** {banned_users}\n\n"
        "Use the buttons below to manage the database."
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Add New Data", callback_data="add_data")],
        [InlineKeyboardButton("📋 View Pending Requests", callback_data="view_requests")],
        [InlineKeyboardButton("👥 Manage Approved Users", callback_data="manage_users")],
        [InlineKeyboardButton("🔍 Search Data", callback_data="search_data")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# عرض الطلبات المعلقة
async def show_pending_requests(query, context):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM join_requests WHERE status = "pending" ORDER BY request_date DESC')
    requests = cursor.fetchall()
    conn.close()
    
    if not requests:
        await query.edit_message_text("🎉 No pending requests found.")
        return
    
    text = "⏳ **Pending Join Requests**\n\n"
    keyboard = []
    
    for req in requests:
        user_id, username, first_name, request_date, status = req
        text += f"👤 **{first_name}**\n"
        text += f"   📱 @{username}\n" if username else "   📱 No username\n"
        text += f"   🆔 `{user_id}`\n"
        text += f"   📅 {request_date[:16]}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ {first_name[:15]}", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(f"❌ {first_name[:15]}", callback_data=f"reject_{user_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# عرض المستخدمين المعتمدين
async def show_approved_users(query, context):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT au.user_id, au.username, au.first_name, au.approved_date, 
               COUNT(ud.id) as data_entries
        FROM approved_users au
        LEFT JOIN users_data ud ON au.user_id = ud.added_by
        WHERE au.status = "active" AND au.user_id != ?
        GROUP BY au.user_id
        ORDER BY au.approved_date DESC
    ''', (OWNER_ID,))
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("No approved users found.")
        return
    
    text = "✅ **Approved Users Management**\n\n"
    keyboard = []
    
    for user in users:
        user_id, username, first_name, approved_date, data_entries = user
        text += f"👤 **{first_name}**\n"
        text += f"   📱 @{username}\n" if username else "   📱 No username\n"
        text += f"   🆔 `{user_id}`\n"
        text += f"   📅 Approved: {approved_date[:16]}\n"
        text += f"   📊 Data Entries: {data_entries}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"🚫 Ban {first_name[:12]}", callback_data=f"ban_{user_id}")
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🚫 View Banned Users", callback_data="view_banned_users")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# عرض المستخدمين المحظورين
async def show_banned_users(query, context):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM banned_users ORDER BY banned_date DESC')
    banned_users = cursor.fetchall()
    conn.close()
    
    if not banned_users:
        await query.edit_message_text("No banned users found.")
        return
    
    text = "🚫 **Banned Users**\n\n"
    keyboard = []
    
    for user in banned_users:
        user_id, username, first_name, banned_date, banned_by, reason = user
        text += f"👤 **{first_name}**\n"
        text += f"   📱 @{username}\n" if username else "   📱 No username\n"
        text += f"   🆔 `{user_id}`\n"
        text += f"   📅 Banned: {banned_date[:16]}\n"
        text += f"   📝 Reason: {reason or 'No reason provided'}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ Unban {first_name[:12]}", callback_data=f"unban_{user_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to User Management", callback_data="manage_users")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# معالجة إدارة المستخدمين
async def handle_user_management(query, context, data):
    if data == "view_banned_users":
        await show_banned_users(query, context)
        return
    
    action, target_user_id = data.split('_')
    target_user_id = int(target_user_id)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if action == "ban":
        # الحصول على بيانات المستخدم
        cursor.execute('SELECT username, first_name FROM approved_users WHERE user_id = ?', (target_user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            username, first_name = user_data
            
            # نقل المستخدم إلى جدول المحظورين
            cursor.execute(
                'INSERT INTO banned_users (user_id, username, first_name, banned_by) VALUES (?, ?, ?, ?)',
                (target_user_id, username, first_name, query.from_user.id)
            )
            
            # تحديث حالة المستخدم في جدول المعتمدين
            cursor.execute('UPDATE approved_users SET status = "banned" WHERE user_id = ?', (target_user_id,))
            
            conn.commit()
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="🚫 **Access Revoked**\n\n"
                         "Your access to the bot has been revoked by the owner.\n"
                         "You can no longer search user data."
                )
            except Exception as e:
                logger.error(f"Could not notify user: {e}")
            
            await query.edit_message_text(f"🚫 User **{first_name}** (@{username}) has been banned.", parse_mode='Markdown')
    
    elif action == "unban":
        # الحصول على بيانات المستخدم المحظور
        cursor.execute('SELECT username, first_name FROM banned_users WHERE user_id = ?', (target_user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            username, first_name = user_data
            
            # إزالة المستخدم من جدول المحظورين
            cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (target_user_id,))
            
            # إزالة المستخدم من جدول المعتمدين (سيحتاج إلى موافقة جديدة)
            cursor.execute('DELETE FROM approved_users WHERE user_id = ?', (target_user_id,))
            
            conn.commit()
            
            await query.edit_message_text(f"✅ User **{first_name}** (@{username}) has been unbanned.\n\nThey will need to send a new join request to use the bot again.", parse_mode='Markdown')
    
    conn.close()

# معالجة قرارات الموافقة/الرفض
async def handle_request_decision(query, context, data):
    action, target_user_id = data.split('_')
    target_user_id = int(target_user_id)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if action == "approve":
        # الحصول على بيانات المستخدم
        cursor.execute('SELECT username, first_name FROM join_requests WHERE user_id = ?', (target_user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            username, first_name = user_data
            # إضافة المستخدم للمستخدمين المعتمدين
            cursor.execute(
                'INSERT OR REPLACE INTO approved_users (user_id, username, first_name, status) VALUES (?, ?, ?, ?)',
                (target_user_id, username, first_name, 'active')
            )
            # تحديث حالة الطلب
            cursor.execute('UPDATE join_requests SET status = ? WHERE user_id = ?', ('approved', target_user_id))
            conn.commit()
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="✅ **Request Approved**\n\n"
                         "Your request has been approved! You can now use the bot.\n"
                         "Use /start to begin searching user data."
                )
            except Exception as e:
                logger.error(f"Could not notify user: {e}")
            
            await query.edit_message_text(f"✅ User **{first_name}** (@{username}) has been approved.", parse_mode='Markdown')
    
    elif action == "reject":
        cursor.execute('SELECT username, first_name FROM join_requests WHERE user_id = ?', (target_user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            username, first_name = user_data
            cursor.execute('UPDATE join_requests SET status = ? WHERE user_id = ?', ('rejected', target_user_id))
            conn.commit()
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="❌ **Request Rejected**\n\n"
                         "Your request to use the bot has been rejected.\n"
                         "Contact the bot owner for more information."
                )
            except Exception as e:
                logger.error(f"Could not notify user: {e}")
            
            await query.edit_message_text(f"❌ User **{first_name}** (@{username}) has been rejected.", parse_mode='Markdown')
    
    conn.close()

# معالجة إدخال البيانات
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # التحقق إذا كان المستخدم محظوراً
    if is_banned_user(user_id):
        await update.message.reply_text(
            "🚫 **Access Denied**\n\n"
            "You have been banned from using this bot.\n"
            "Contact the bot owner for more information."
        )
        return
    
    if user_id == OWNER_ID and context.user_data.get('awaiting_data'):
        await process_user_data(update, context, message_text)
    
    elif is_approved_user(user_id) and context.user_data.get('searching'):
        await search_user_data(update, context, message_text)
    
    else:
        if user_id == OWNER_ID:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")
        elif is_approved_user(user_id):
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")
        else:
            await update.message.reply_text("📨 Your request has been sent to the owner and is pending approval.")

# معالجة بيانات المستخدم الجديدة
async def process_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    try:
        lines = message_text.split('\n')
        data_dict = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                data_dict[key.strip().lower()] = value.strip()
        
        required_fields = ['name', 'user id']
        for field in required_fields:
            if field not in data_dict:
                await update.message.reply_text(f"❌ Missing required field: {field}")
                return
        
        name = data_dict['name']
        user_id = data_dict['user id']
        username = data_dict.get('username', '').replace('@', '')
        location = data_dict.get('location', '')
        more_info = data_dict.get('more info', '')
        
        # التحقق من التكرار
        if is_duplicate_data(user_id):
            await update.message.reply_text("❌ This user data already exists in the database.")
            return
        
        # حفظ البيانات
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users_data (name, username, user_id, location, more_info, added_by) VALUES (?, ?, ?, ?, ?, ?)',
            (name, username, user_id, location, more_info, update.effective_user.id)
        )
        conn.commit()
        conn.close()
        
        # تأكيد الإضافة
        confirmation_text = (
            "✅ **User Data Added Successfully!**\n\n"
            f"👤 **Name:** {name}\n"
            f"📱 **Username:** @{username}\n" if username else "📱 **Username:** Not provided\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📍 **Location:** {location}\n" if location else "📍 **Location:** Not provided\n"
            f"📄 **More Info:** {more_info}\n" if more_info else "📄 **More Info:** Not provided\n"
        )
        
        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        context.user_data['awaiting_data'] = False
        
    except Exception as e:
        logger.error(f"Error processing user data: {e}")
        await update.message.reply_text("❌ Error processing data. Please check the format and try again.")

# البحث في بيانات المستخدمين
async def search_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE, search_term: str):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    search_term = f"%{search_term}%"
    cursor.execute('''
        SELECT name, username, user_id, location, more_info 
        FROM users_data 
        WHERE name LIKE ? OR username LIKE ? OR user_id LIKE ? OR location LIKE ? OR more_info LIKE ?
    ''', (search_term, search_term, search_term, search_term, search_term))
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        await update.message.reply_text("❌ No matching user data found.")
        context.user_data['searching'] = False
        return
    
    response = f"🔍 **Search Results for '{search_term[1:-1]}'**\n\n"
    response += f"📊 **Found {len(results)} result(s)**\n\n"
    
    for i, (name, username, user_id, location, more_info) in enumerate(results, 1):
        response += f"**{i}. User Data:**\n"
        response += f"   👤 **Name:** {name}\n"
        response += f"   📱 **Username:** @{username}\n" if username else "   📱 **Username:** Not provided\n"
        response += f"   🆔 **User ID:** `{user_id}`\n"
        response += f"   📍 **Location:** {location}\n" if location else "   📍 **Location:** Not provided\n"
        response += f"   📄 **More Info:** {more_info}\n" if more_info else "   📄 **More Info:** Not provided\n"
        response += "   " + "─" * 30 + "\n\n"
    
    # تقسيم الرسالة إذا كانت طويلة جداً
    if len(response) > 4096:
        parts = []
        while len(response) > 4096:
            part = response[:4096]
            last_newline = part.rfind('\n')
            if last_newline != -1:
                parts.append(part[:last_newline])
                response = response[last_newline+1:]
            else:
                parts.append(part)
                response = response[4096:]
        parts.append(response)
        
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(response, parse_mode='Markdown')
    
    context.user_data['searching'] = False

# الرجوع للقائمة الرئيسية
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("➕ Add New Data", callback_data="add_data")],
            [InlineKeyboardButton("📋 View Pending Requests", callback_data="view_requests")],
            [InlineKeyboardButton("👥 Manage Approved Users", callback_data="manage_users")],
            [InlineKeyboardButton("🔍 Search User Data", callback_data="search_data")],
            [InlineKeyboardButton("📊 Database Stats", callback_data="db_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👑 **Owner Panel**\n\n"
            "Welcome back, Owner! Choose an option:",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Search User Data", callback_data="search_data")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔍 **User Data Search Bot**\n\n"
            "Welcome! Use the button below to search for user data:",
            reply_markup=reply_markup
        )

# دالة الرئيسية
def main():
    # تهيئة قاعدة البيانات
    init_db()
    add_owner_to_approved()
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button, pattern="^(add_data|view_requests|manage_users|search_data|db_stats|approve_|reject_|ban_|unban_|view_banned_)"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # بدء البوت
    print("🤖 Bot is running...")
    print("👑 Owner ID:", OWNER_ID)
    print("💾 Database initialized successfully")
    print("🚀 Deployed on Render.com")
    application.run_polling()

if __name__ == '__main__':
    main()