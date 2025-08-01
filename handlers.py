# handlers.py
import logging, uuid, datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
)
import keyboards, config, database, kmsp_api

logger = logging.getLogger(__name__)

# --- Definisi State ---
ROUTE = chr(0)
(PURCHASE_ASK_PHONE_NUMBER, PURCHASE_ASK_PACKAGE, PURCHASE_CONFIRM) = map(chr, range(3))

# --- Fungsi Dasar Bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    database.add_user_if_not_exists(user.id, user.first_name, user.username)
    await update.message.reply_text(
        "🤖 Selamat Datang di Bot Pembelian Paket Data!\n\nGunakan menu di bawah untuk memulai.",
        reply_markup=keyboards.main_menu_keyboard()
    )
    return ROUTE

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_chat.send_message(
        "Silakan pilih dari menu:",
        reply_markup=keyboards.main_menu_keyboard()
    )
    return ROUTE
    
async def route_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "main_menu":
        await query.edit_message_text("Menu Utama:", reply_markup=keyboards.main_menu_keyboard())
    elif query.data == "close_menu":
        await query.edit_message_text("Menu ditutup. Ketik /start untuk membuka lagi.")
    else:
        logger.warning(f"Unhandled callback: {query.data}")
        await query.edit_message_text("Tombol tidak valid.")
    return ROUTE

# --- Handler Alur Pembelian ---
async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="➡️ Silakan masukkan nomor XL/Axis tujuan (contoh: 087812345678).")
    return PURCHASE_ASK_PHONE_NUMBER

async def ask_package(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone_number = update.message.text.strip()
    if not (phone_number.startswith('08') and len(phone_number) > 9 and phone_number.isdigit()):
        await update.message.reply_text("❌ Format nomor salah. Silakan coba lagi.")
        return PURCHASE_ASK_PHONE_NUMBER
    context.user_data['phone_number'] = phone_number
    await update.message.reply_text("⏳ Mengambil daftar paket, mohon tunggu...")
    packages = database.get_all_packages()
    if not packages:
        await update.message.reply_text("Gagal mengambil daftar paket. Coba lagi nanti.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(f"{p['package_name']} - Rp{p['harga_final']:,}", callback_data=f"pkg_{p['package_code']}")] for p in packages[:25]]
    await update.message.reply_text("Silakan pilih paket:", reply_markup=InlineKeyboardMarkup(buttons))
    return PURCHASE_ASK_PACKAGE

async def ask_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['package_code'] = query.data.replace('pkg_', '')
    await query.edit_message_text("⏳ Memeriksa detail...")
    pkg_details = database.get_package_details(context.user_data['package_code'])
    user_data = database.get_user_balance(update.effective_user.id)
    if not pkg_details or not user_data or user_data.get('balance') is None:
        await query.edit_message_text("Gagal mengambil data user/paket.")
        return ConversationHandler.END
    harga_paket = int(pkg_details['harga_final'])
    context.user_data.update({'harga_paket': harga_paket, 'harga_kmsp': int(pkg_details.get('harga_kmsp') or 0)})
    if user_data['balance'] < harga_paket:
        await query.edit_message_text(f"Saldo Anda (Rp{user_data['balance']:,}) tidak cukup.")
        return ConversationHandler.END
    text = (f"🔔 **Konfirmasi Pembelian**\n\n"
            f"📞 **Nomor:** `{context.user_data['phone_number']}`\n"
            f"📦 **Paket:** {pkg_details['package_name']}\n"
            f"💰 **Harga:** Rp{harga_paket:,}\n\n"
            f"Anda yakin ingin melanjutkan?")
    await query.edit_message_text(text=text, reply_markup=keyboards.purchase_confirmation_keyboard(), parse_mode='Markdown')
    return PURCHASE_CONFIRM

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Konfirmasi diterima. Memproses transaksi ke server...")
    ud = context.user_data
    result = kmsp_api.purchase_package(ud['package_code'], ud['phone_number'], 'DANA', ud['harga_kmsp'])
    user_info = database.get_user_balance(update.effective_user.id)
    pkg_details = database.get_package_details(ud['package_code'])
    if result and result.get('status'):
        database.update_user_balance(user_info['username'], user_info['balance'] - ud['harga_paket'])
        msg, trx_id, status_log = result.get('message', 'Sukses!'), result.get('data', {}).get('trx_id', 'N/A'), 'success'
        await query.edit_message_text(f"✅ **BERHASIL!**\n\n{msg}\n**ID Transaksi:** `{trx_id}`", parse_mode='Markdown')
    else:
        msg, status_log = result.get('message', 'Gagal dari server.'), 'error'
        await query.edit_message_text(f"❌ **GAGAL!**\n\n{msg}")
    log_data = {'wid': 'W'+str(uuid.uuid4().int)[:9],'tid': result.get('data',{}).get('trx_id','T'+str(uuid.uuid4().int)[:9]),'user': user_info.get('username'),'code': ud['package_code'],'name': pkg_details['package_name'],'data': ud['phone_number'],'note': msg,'price': ud['harga_paket'],'status': status_log,'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    database.log_transaction(log_data)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_chat.send_message("❌ Operasi dibatalkan.", reply_markup=keyboards.main_menu_keyboard())
    return ConversationHandler.END

async def back_to_menu_from_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Dibatalkan. Kembali ke menu utama.", reply_markup=keyboards.main_menu_keyboard())
    return ConversationHandler.END

# --- Definisi Conversation Handler ---
purchase_xl_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_purchase, pattern='^purchase_xl_start$')],
    states={
        PURCHASE_ASK_PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_package)],
        PURCHASE_ASK_PACKAGE: [CallbackQueryHandler(ask_confirmation, pattern='^pkg_')],
        PURCHASE_CONFIRM: [
            CallbackQueryHandler(process_purchase, pattern='^confirm_purchase_yes$'),
            CallbackQueryHandler(cancel, pattern='^confirm_purchase_no$'),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', cancel), CommandHandler('start', start),
        CallbackQueryHandler(back_to_menu_from_conv, pattern='^main_menu$'),
        CallbackQueryHandler(cancel, pattern='^close_menu$')
    ],
    per_user=True, conversation_timeout=300
)
