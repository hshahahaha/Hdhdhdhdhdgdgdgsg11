#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام لفحص البطاقات عبر بوابة Braintree
مع إحصائيات مباشرة تتحدث كل ثانية
"""

import os
import sys
import time
import asyncio
import logging
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from braintree_checker import BraintreeChecker

# التكوين المباشر - لا حاجة للمتغيرات البيئية
TELEGRAM_BOT_TOKEN = '8330401921:AAE1hZYp8ws4P7ZZg74WFFL2Sf8hNlKN-Sw'
ADMIN_USER_ID = 1427023555

# إعداد السجلات
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# تخزين حالة الفحص والإحصائيات
checking_status = {}
user_stats = {}
command_cooldown = {}


def parse_card(text):
    """استخراج بيانات البطاقة من النص"""
    text = text.strip().replace(' ', '').replace('\n', '')
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    match = re.search(pattern, text)
    
    if match:
        card_number = match.group(1)
        exp_month = match.group(2).zfill(2)
        exp_year = match.group(3)
        cvv = match.group(4)
        
        if len(exp_year) == 4:
            exp_year = exp_year[2:]
        
        return f"{card_number}|{exp_month}|{exp_year}|{cvv}"
    
    return None


def get_bin_info(bin_number):
    """الحصول على معلومات BIN (مبسطة)"""
    return f"[ϟ] 𝐁𝐢𝐧: {bin_number}\n[ϟ] 𝐈𝐧𝐟𝐨: Card Information"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    keyboard = [[InlineKeyboardButton("🚀 Start Checking", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sent_message = await update.message.reply_text("💥 Starting...")
    await asyncio.sleep(1)
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=sent_message.message_id,
        text=f"Hi {user.first_name}, Welcome To Saoud Checker (Brantree Auth)",
        reply_markup=reply_markup
    )
    
    logger.info(f"User {user_id} ({user.first_name}) started the bot")


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج زر Start"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    instructions = """- مرحباً بك في بوت فحص Brantree Auth ✅


للفحص اليدوي [/chk] و للكومبو فقط ارسل الملف.

اختر نوع الفحص وسيبدأ البوت بأعطائك افضل النتائج مع علاوي الاسطوره @B11HB"""
    
    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=instructions
    )
    
    await query.edit_message_text(
        text=f"Hi {user.first_name}, Welcome To Saoud Checker (Brantree Auth)",
        reply_markup=query.message.reply_markup
    )


async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /chk لفحص بطاقة واحدة"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الكولداون (10 ثواني)
    if user_id in command_cooldown:
        time_diff = (datetime.now() - command_cooldown[user_id]).seconds
        if time_diff < 10:
            await update.message.reply_text(
                f"<b>Try again after {10 - time_diff} seconds.</b>",
                parse_mode="HTML"
            )
            return
    
    # الحصول على بيانات البطاقة
    if update.message.reply_to_message:
        card_data = parse_card(update.message.reply_to_message.text)
    elif context.args:
        card_data = parse_card(' '.join(context.args))
    else:
        card_data = parse_card(update.message.text.replace('/chk', '').replace('.chk', ''))
    
    if not card_data:
        await update.message.reply_text(
            """<b>🚫 Oops!
Please ensure you enter the card details in the correct format:
Card: XXXXXXXXXXXXXXXX|MM|YYYY|CVV</b>""",
            parse_mode="HTML"
        )
        return
    
    # إرسال رسالة الانتظار
    status_msg = await update.message.reply_text("- Wait checking your card ...")
    
    # تحديث الكولداون
    command_cooldown[user_id] = datetime.now()
    
    # بدء الفحص
    start_time = time.time()
    
    try:
        checker = BraintreeChecker()
        result = await asyncio.to_thread(checker.check_card, card_data)
    except Exception as e:
        logger.error(f"Error checking card: {e}")
        result = {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'card_type': 'Unknown',
            'amount': '5.00'
        }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # تحديد الحالة
    if result['status'] == 'approved' or '1000: Approved' in result['message']:
        status_text = 'Approved Auth! ✅'
    else:
        status_text = 'DECLINED! ❌'
    
    # تنسيق الرسالة
    bin_info = get_bin_info(card_data[:6])
    
    response_message = f"""<strong>#Brantree_Auth 🔥 [/chk]
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/B">ϟ</a>] 𝐂𝐚𝐫𝐝: <code>{card_data}</code>
[<a href="https://t.me/B">ϟ</a>] 𝐒𝐭𝐚𝐭𝐮𝐬: <code>{status_text}</code>
[<a href="https://t.me/B">ϟ</a>] 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{result['message']}</code>
- - - - - - - - - - - - - - - - - - - - - - -
{bin_info}
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/B">⌥</a>] 𝐓𝐢𝐦𝐞: <code>{execution_time:.2f}'s</code>
[<a href="https://t.me/B">⌥</a>] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐛𝐲: <a href='tg://user?id={user_id}'>{user.first_name}</a>
- - - - - - - - - - - - - - - - - - - - - - -
[<a href="https://t.me/B">⌤</a>] 𝐃𝐞𝐯 𝐛𝐲: <a href='tg://user?id=1427023555'>XJX</a> - 🍀</strong>"""
    
    await status_msg.edit_text(response_message, parse_mode="HTML")
    
    # تحديث الإحصائيات
    if user_id not in user_stats:
        user_stats[user_id] = {'total': 0, 'approved': 0, 'declined': 0, 'errors': 0}
    
    user_stats[user_id]['total'] += 1
    if result['status'] == 'approved':
        user_stats[user_id]['approved'] += 1
    elif result['status'] == 'declined':
        user_stats[user_id]['declined'] += 1
    else:
        user_stats[user_id]['errors'] += 1
    
    logger.info(f"User {user_id} checked card: ****{card_data[-4:]} - {result['status']}")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الملفات للفحص الجماعي"""
    user = update.effective_user
    user_id = user.id
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            "❌ <b>خطأ!</b> الرجاء إرسال ملف نصي (.txt) فقط.",
            parse_mode='HTML'
        )
        return
    
    # تنزيل الملف
    os.makedirs('data', exist_ok=True)
    file = await context.bot.get_file(document.file_id)
    file_path = f"data/{user_id}_{int(time.time())}.txt"
    await file.download_to_drive(file_path)
    
    # قراءة البطاقات
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>خطأ في قراءة الملف:</b> {str(e)}",
            parse_mode='HTML'
        )
        return
    
    # استخراج البطاقات
    cards = []
    for line in lines:
        card = parse_card(line)
        if card:
            cards.append(card)
    
    if not cards:
        await update.message.reply_text(
            "❌ <b>لم يتم العثور على بطاقات صالحة!</b>",
            parse_mode='HTML'
        )
        return
    
    # رسالة البداية
    start_msg = await update.message.reply_text(
        f"""🚀 <b>بدء الفحص الجماعي</b>

📊 عدد البطاقات: <code>{len(cards)}</code>
⏳ جاري التحضير...""",
        parse_mode='HTML'
    )
    
    # إحصائيات الفحص
    stats = {
        'total': len(cards),
        'checked': 0,
        'approved': 0,
        'declined': 0,
        'errors': 0,
        'start_time': time.time()
    }
    
    # حفظ حالة الفحص
    checking_status[user_id] = {
        'active': True,
        'stats': stats,
        'message_id': start_msg.message_id,
        'chat_id': update.effective_chat.id
    }
    
    # بدء تحديث الإحصائيات
    asyncio.create_task(update_stats_live(context, user_id))
    
    # ملف النتائج
    results_file = f"data/results_{user_id}_{int(time.time())}.txt"
    approved_file = f"data/approved_{user_id}_{int(time.time())}.txt"
    
    # تهيئة الفاحص
    checker = BraintreeChecker()
    
    # فحص البطاقات
    with open(results_file, 'w', encoding='utf-8') as f_all, \
         open(approved_file, 'w', encoding='utf-8') as f_approved:
        
        f_all.write("=" * 60 + "\n")
        f_all.write("نتائج الفحص الكامل - Braintree Auth\n")
        f_all.write("=" * 60 + "\n\n")
        
        f_approved.write("=" * 60 + "\n")
        f_approved.write("البطاقات المقبولة فقط - Braintree Auth\n")
        f_approved.write("=" * 60 + "\n\n")
        
        for i, card in enumerate(cards, 1):
            if not checking_status[user_id]['active']:
                break
            
            try:
                result = await asyncio.to_thread(checker.check_card, card)
            except Exception as e:
                logger.error(f"Error checking card {i}: {e}")
                result = {
                    'status': 'error',
                    'message': f'Error: {str(e)}',
                    'card_type': 'Unknown',
                    'amount': '5.00'
                }
            
            # تحديث الإحصائيات
            stats['checked'] += 1
            
            if result['status'] == 'approved' or '1000: Approved' in result['message']:
                stats['approved'] += 1
                status_symbol = "✅"
                
                # حفظ في ملف المقبولة
                f_approved.write(f"✅ {card}\n")
                f_approved.write(f"   الرد: {result['message']}\n\n")
                f_approved.flush()
            elif result['status'] == 'declined':
                stats['declined'] += 1
                status_symbol = "❌"
            else:
                stats['errors'] += 1
                status_symbol = "⚠️"
            
            # حفظ في ملف النتائج الكامل
            f_all.write(f"{status_symbol} البطاقة #{i}:\n")
            f_all.write(f"   {card}\n")
            f_all.write(f"   الحالة: {result['message']}\n")
            f_all.write(f"   النوع: {result.get('card_type', 'Unknown')}\n\n")
            f_all.flush()
            
            # انتظار ثانية بين البطاقات
            await asyncio.sleep(1)
    
    # إنهاء الفحص
    checking_status[user_id]['active'] = False
    
    # حساب الوقت الإجمالي
    total_time = time.time() - stats['start_time']
    
    # رسالة النهاية
    final_message = f"""✅ <b>اكتمل الفحص الجماعي!</b>

📊 <b>الإحصائيات النهائية:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 📝 الإجمالي: <code>{stats['total']}</code>
• ✅ المقبولة: <code>{stats['approved']}</code>
• ❌ المرفوضة: <code>{stats['declined']}</code>
• ⚠️ أخطاء: <code>{stats['errors']}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱ الوقت الإجمالي: <code>{total_time:.2f}s</code>
📁 تم حفظ النتائج في الملفات المرفقة"""
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=start_msg.message_id,
        text=final_message,
        parse_mode='HTML'
    )
    
    # إرسال ملف النتائج الكامل
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=open(results_file, 'rb'),
        caption="📄 <b>ملف النتائج الكامل</b>",
        parse_mode='HTML'
    )
    
    # إرسال ملف المقبولة إذا كان هناك بطاقات مقبولة
    if stats['approved'] > 0:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(approved_file, 'rb'),
            caption=f"✅ <b>البطاقات المقبولة ({stats['approved']})</b>",
            parse_mode='HTML'
        )
    
    # تحديث إحصائيات المستخدم
    if user_id not in user_stats:
        user_stats[user_id] = {'total': 0, 'approved': 0, 'declined': 0, 'errors': 0}
    
    user_stats[user_id]['total'] += stats['checked']
    user_stats[user_id]['approved'] += stats['approved']
    user_stats[user_id]['declined'] += stats['declined']
    user_stats[user_id]['errors'] += stats['errors']
    
    logger.info(f"User {user_id} completed bulk check: {stats['checked']} cards, {stats['approved']} approved")


async def update_stats_live(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """تحديث الإحصائيات المباشرة كل ثانية"""
    while checking_status.get(user_id, {}).get('active', False):
        try:
            stats = checking_status[user_id]['stats']
            message_id = checking_status[user_id]['message_id']
            chat_id = checking_status[user_id]['chat_id']
            
            # حساب النسب المئوية
            if stats['checked'] > 0:
                approved_percent = (stats['approved'] / stats['checked']) * 100
                declined_percent = (stats['declined'] / stats['checked']) * 100
                error_percent = (stats['errors'] / stats['checked']) * 100
            else:
                approved_percent = declined_percent = error_percent = 0
            
            # حساب التقدم
            progress = (stats['checked'] / stats['total']) * 100
            progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
            
            # حساب الوقت
            elapsed_time = time.time() - stats['start_time']
            
            if stats['checked'] > 0:
                avg_time = elapsed_time / stats['checked']
                remaining_cards = stats['total'] - stats['checked']
                estimated_time = avg_time * remaining_cards
            else:
                estimated_time = 0
            
            # تنسيق الرسالة
            stats_message = f"""🚀 <b>الفحص الجماعي قيد التنفيذ...</b>

📊 <b>التقدم:</b> <code>{progress:.1f}%</code>
{progress_bar}

<b>📈 الإحصائيات المباشرة:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 📝 تم الفحص: <code>{stats['checked']}/{stats['total']}</code>
• ✅ مقبولة: <code>{stats['approved']}</code> (<code>{approved_percent:.1f}%</code>)
• ❌ مرفوضة: <code>{stats['declined']}</code> (<code>{declined_percent:.1f}%</code>)
• ⚠️ أخطاء: <code>{stats['errors']}</code> (<code>{error_percent:.1f}%</code>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱ الوقت المنقضي: <code>{int(elapsed_time)}s</code>
⏳ الوقت المتبقي: <code>~{int(estimated_time)}s</code>

💡 <b>نصيحة:</b> لا تغلق البوت حتى اكتمال الفحص!"""
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=stats_message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
        
        await asyncio.sleep(1)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /stats"""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_stats or user_stats[user_id]['total'] == 0:
        await update.message.reply_text(
            "📊 <b>لا توجد إحصائيات بعد!</b>\n\nابدأ بفحص بعض البطاقات أولاً.",
            parse_mode='HTML'
        )
        return
    
    stats = user_stats[user_id]
    
    approved_percent = (stats['approved'] / stats['total']) * 100
    declined_percent = (stats['declined'] / stats['total']) * 100
    error_percent = (stats['errors'] / stats['total']) * 100
    
    stats_message = f"""📊 <b>إحصائياتك الشخصية</b>

👤 <b>المستخدم:</b> <a href='tg://user?id={user_id}'>{user.first_name}</a>

<b>📈 الإحصائيات الإجمالية:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 📝 إجمالي الفحوصات: <code>{stats['total']}</code>
• ✅ بطاقات مقبولة: <code>{stats['approved']}</code> (<code>{approved_percent:.1f}%</code>)
• ❌ بطاقات مرفوضة: <code>{stats['declined']}</code> (<code>{declined_percent:.1f}%</code>)
• ⚠️ أخطاء: <code>{stats['errors']}</code> (<code>{error_percent:.1f}%</code>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>المطور:</b> @B11HB"""
    
    await update.message.reply_text(stats_message, parse_mode='HTML')


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء"""
    logger.error(f"Exception: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ <b>حدث خطأ!</b> الرجاء المحاولة مرة أخرى.",
                parse_mode='HTML'
            )
    except:
        pass


def main():
    """الدالة الرئيسية"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        sys.exit(1)
    
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(start_callback, pattern="^start$"))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_file))
    application.add_handler(MessageHandler(filters.Regex(r'^\.chk'), chk_command))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء البوت
    logger.info("🚀 Bot is running...")
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
