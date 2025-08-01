# handlers.py
import logging
import uuid
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
)
import keyboards, config, database, kmsp_api

logger = logging.getLogger(__name__)

# --- Definisi State ---
ROUTE = chr(0)
(PURCHASE_ASK_PHONE_NUMBER, PURCHASE_ASK_PACKAGE, PURCHASE_CONFIRM) = map(chr, range(3))
(OTP_ASK_PHONE, OTP_ASK_CODE) = map(chr, range(4, 6))

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
    elif query.data == "panel_xl_menu":
        if context.user_data.get('access_token'):
            await query.edit_message_text(
                text=f"Anda sudah login dengan nomor: `{context.user_data.get('phone')}`\nSilakan pilih menu panel:",
                reply_markup=keyboards.panel_xl_keyboard(), parse_mode='Markdown'
            )
        else:
            await start_otp_login(update, context)
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
        await query.edit_message_text(f"✅ **BERHASIL!**\n\n{msg}\n**ID Transaksi:** `{trx_id}`", parse_mode='Markdown', reply_markup=keyboards.main_menu_keyboard())
    else:
        msg, status_log = result.get('message', 'Gagal dari server.'), 'error'
        await query.edit_message_text(f"❌ **GAGAL!**\n\n{msg}", reply_markup=keyboards.main_menu_keyboard())
    log_data = {'wid': 'W'+str(uuid.uuid4().int)[:9],'tid': result.get('data',{}).get('trx_id','T'+str(uuid.uuid4().int)[:9]),'user': user_info.get('username'),'code': ud['package_code'],'name': pkg_details['package_name'],'data': ud['phone_number'],'note': msg,'price': ud['harga_paket'],'status': status_log,'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    database.log_transaction(log_data)
    return ConversationHandler.END

# --- Handler Alur Login OTP ---
async def start_otp_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = "🔒 Untuk mengakses Panel XL, silakan login terlebih dahulu.\n\nMasukkan nomor XL/Axis Anda (format: 628...):"
    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    else:
        await update.message.reply_text(text=message_text)
    return OTP_ASK_PHONE

async def receive_phone_for_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    if not (phone.startswith('628') and phone.isdigit() and len(phone) > 10):
        await update.message.reply_text("Format nomor salah. Harap gunakan awalan 628. Coba lagi:")
        return OTP_ASK_PHONE
    await update.message.reply_text(f"⏳ Mengirim kode OTP ke {phone}, mohon tunggu...")
    result = kmsp_api.request_otp(phone)
    if result and result.get('status'):
        context.user_data['auth_id'] = result['data']['auth_id']
        context.user_data['phone'] = phone
        await update.message.reply_text("✅ OTP berhasil terkirim! Masukkan 6 digit kode OTP di sini.")
        return OTP_ASK_CODE
    else:
        await update.message.reply_text(f"❌ Gagal: {result.get('message', 'Gagal mengirim OTP.')}\n\nCoba lagi atau /cancel.")
        return OTP_ASK_PHONE

async def receive_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    otp_code = update.message.text.strip()
    auth_id, phone = context.user_data.get('auth_id'), context.user_data.get('phone')
    await update.message.reply_text(f"🔑 Memverifikasi kode OTP...")
    result = kmsp_api.login_with_otp(phone, auth_id, otp_code)
    if result and result.get('status'):
        context.user_data['access_token'] = result['data']['access_token']
        await update.message.reply_text(
            text=f"✅ Login Berhasil! Panel XL untuk nomor `{phone}` aktif.",
            reply_markup=keyboards.panel_xl_keyboard(), parse_mode='Markdown'
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"❌ Gagal: {result.get('message', 'OTP salah.')}\n\nMasukkan kode lagi, atau /cancel.")
        return OTP_ASK_CODE

# --- Handler Fitur Panel ---
async def check_pulsa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Memeriksa pulsa...")
    access_token = context.user_data.get('access_token')
    if not access_token:
        await query.edit_message_text("Sesi berakhir. Silakan login kembali.", reply_markup=keyboards.main_menu_keyboard())
        return
    result = kmsp_api.get_subscriber_info(access_token)
    if result and result.get('status'):
        data = result['data']
        text = (f"💰 **Informasi Pulsa & Nomor**\n\n"
                f"Nomor: `{data['msisdn']}`\n"
                f"Status: *{data['subscription_status']}*\n"
                f"Pulsa Utama: *{data['pulsa_real']}*\n"
                f"Masa Aktif s/d: `{data['active_until']}`")
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboards.panel_xl_keyboard())
    else:
        await query.edit_message_text(f"Gagal: {result.get('message')}", reply_markup=keyboards.panel_xl_keyboard())

async def check_lokasi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Memeriksa lokasi...")
    access_token = context.user_data.get('access_token')
    if not access_token:
        await query.edit_message_text("Sesi berakhir. Silakan login kembali.", reply_markup=keyboards.main_menu_keyboard())
        return
    result = kmsp_api.get_subscriber_location(access_token)
    if result and result.get('status'):
        text = f"📍 **Lokasi Terdeteksi:**\n`{result['data']['location']}`"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboards.panel_xl_keyboard())
    else:
        await query.edit_message_text(f"Gagal: {result.get('message')}", reply_markup=keyboards.panel_xl_keyboard())

async def check_paket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Memeriksa paket aktif...")
    access_token = context.user_data.get('access_token')
    if not access_token:
        await query.edit_message_text("Sesi berakhir. Silakan login kembali.", reply_markup=keyboards.main_menu_keyboard())
        return
    result = kmsp_api.get_quota_details(access_token)
    if result and result.get('status') and result['data']['quotas']:
        text = "📦 **Daftar Paket Aktif Anda:**\n\n"
        buttons = []
        for paket in result['data']['quotas']:
            text += f"🔹 **{paket['name']}**\n   _Expired: {paket['expired_at']}_\n\n"
            buttons.append([InlineKeyboardButton(f"Stop: {paket['name']}", callback_data=f"unreg_{paket['encrypted_package_code']}")])
        buttons.append([InlineKeyboardButton("⬅️ Kembali ke Panel", callback_data="panel_xl_menu")])
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(result.get('message', "Tidak ada paket aktif."), reply_markup=keyboards.panel_xl_keyboard())

async def unreg_paket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    encrypted_code = query.data.replace('unreg_', '')
    await query.answer("Memproses stop paket...")
    access_token = context.user_data.get('access_token')
    if not access_token:
        await query.edit_message_text("Sesi berakhir. Silakan login kembali.", reply_markup=keyboards.main_menu_keyboard())
        return
    result = kmsp_api.unreg_package(access_token, encrypted_code)
    if result and result.get('status'):
        await query.edit_message_text("✅ Paket berhasil dihentikan. Silakan cek ulang.", reply_markup=keyboards.panel_xl_keyboard())
    else:
        await query.edit_message_text(f"Gagal: {result.get('message')}", reply_markup=keyboards.panel_xl_keyboard())

async def logout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data.clear() # Membersihkan semua data sesi
    await query.answer("Logout berhasil!")
    await query.edit_message_text("Anda telah keluar dari Panel XL.", reply_markup=keyboards.main_menu_keyboard())

# --- Fungsi Pembatalan Umum ---
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
        CallbackQueryHandler(back_to_menu_from_conv, pattern='^main_menu$')
    ]
)

otp_login_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_otp_login, pattern='^panel_xl_menu$')],
    states={
        OTP_ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone_for_otp)],
        OTP_ASK_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp_code)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
