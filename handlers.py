import logging
import subprocess
import uuid
import os
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CommandHandler
)

import keyboards
import config
import database

logger = logging.getLogger(__name__)

# --- Definisi State ---
ROUTE = chr(0)
SSH_GET_USERNAME, SSH_GET_PASSWORD, SSH_GET_DURATION, SSH_GET_IP_LIMIT = map(chr, range(1, 5))
VMESS_GET_USER, VMESS_GET_DURATION = map(chr, range(5, 7))
VLESS_GET_USER, VLESS_GET_DURATION, VLESS_GET_IP_LIMIT, VLESS_GET_QUOTA = map(chr, range(7, 11))
TROJAN_GET_USER, TROJAN_GET_DURATION, TROJAN_GET_IP_LIMIT, TROJAN_GET_QUOTA = map(chr, range(11, 15))
RENEW_SSH_GET_USERNAME, RENEW_SSH_GET_DURATION = map(chr, range(15, 17))
# State Trial DIKEMBALIKAN agar cocok dengan main.py
TRIAL_CREATE_SSH, TRIAL_CREATE_VMESS, TRIAL_CREATE_VLESS, TRIAL_CREATE_TROJAN = map(chr, range(18, 22))
DELETE_GET_USERNAME, DELETE_CONFIRMATION = map(chr, range(22, 24))
VMESS_SELECT_ACCOUNT = chr(25)
SSH_SELECT_ACCOUNT = chr(26)
RENEW_VMESS_GET_USERNAME, RENEW_VMESS_GET_DURATION = map(chr, range(27, 29))
# --- TAMBAHAN: STATE BARU UNTUK PEMBELIAN PAKET DATA ---
(
    PURCHASE_ASK_PHONE_NUMBER,
    PURCHASE_ASK_PACKAGE,
    PURCHASE_CONFIRM
) = map(chr, range(30, 33)) # Memulai dari range yang aman
# --- AKHIR TAMBAHAN ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    database.add_user_if_not_exists(user.id, user.first_name, user.username)
    await update.message.reply_text(
        "🤖 Welcome to SSH/VPN Management Bot!\n\n"
        "Use /menu to access all features.",
        reply_markup=keyboards.get_main_menu_keyboard()
    )
    return ROUTE

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_message = update.callback_query.message if update.callback_query else update.message
    if target_message:
        if update.callback_query and target_message.text:
            await target_message.edit_text(
                "Please select from the menu below:",
                reply_markup=keyboards.get_main_menu_keyboard()
            )
        else:
            await update.effective_chat.send_message(
                "Please select from the menu below:",
                reply_markup=keyboards.get_main_menu_keyboard()
            )
    return ROUTE

async def handle_script_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
    msg = f"An unexpected error occurred: {error}"
    if isinstance(error, subprocess.CalledProcessError):
        error_output = error.stdout.strip() or error.stderr.strip()
        msg = error_output or "Script failed with a non-zero exit code but no error output."
    elif isinstance(error, FileNotFoundError):
        msg = f"Script file not found ({error}). Please check the path and permissions."
    elif isinstance(error, TimeoutError):
        msg = "Script execution timed out. It took too long to respond."

    text_to_send = f"❌ Operation Failed\n\nReason:\n{msg}"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text_to_send,
        reply_markup=keyboards.get_back_to_menu_keyboard()
    )
    logger.error(f"Script execution error: {msg}", exc_info=True)
    return ROUTE

async def handle_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    await query.edit_message_text("⏳ Memulai proses backup, mohon tunggu...")

    try:
        script_path = "/opt/hokage-bot/backup_for_bot.sh"
        process = subprocess.run(
            ['sudo', script_path],
            capture_output=True, text=True, check=True, timeout=600
        )

        script_output = process.stdout
        await context.bot.send_message(chat_id, script_output)

        local_file_path = None
        match = re.search(r"LocalPath: (/\S+\.zip)", script_output)
        if match:
            local_file_path = match.group(1).strip()

        if local_file_path and os.path.exists(local_file_path):
            await context.bot.send_message(chat_id, "📤 Mengirim file backup...")
            with open(local_file_path, 'rb') as backup_file:
                await context.bot.send_document(chat_id, document=backup_file)

            os.remove(local_file_path)
            await context.bot.send_message(chat_id, "✅ File backup di server telah dihapus.")
        elif local_file_path:
             await context.bot.send_message(chat_id, f"⚠️ Gagal mengirim file. File tidak ditemukan di: {local_file_path}")
        else:
            await context.bot.send_message(chat_id, "⚠️ Gagal menemukan path file backup di output skrip.")

    except Exception as e:
        await handle_script_error(update, context, e)

    await context.bot.send_message(chat_id, "Proses selesai.", reply_markup=keyboards.get_back_to_menu_keyboard())

    return ROUTE

async def route_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    command = query.data
    user_id = update.effective_user.id
    logger.info(f"User {user_id} selected callback: {command}")

    if command == "menu_backup":
        return await handle_backup(update, context)

    if command == "menu_restore":
        context.user_data['action_to_confirm'] = 'restore'
        await query.edit_message_text(
            "PERINGATAN!\n\nRestore akan menimpa semua data dengan backup terbaru. Lanjutkan?",
            reply_markup=keyboards.get_confirmation_keyboard()
        )
        return ROUTE

    if command in ["main_menu", "back_to_main_menu"]:
        await query.edit_message_text("Main Menu:", reply_markup=keyboards.get_main_menu_keyboard())
        return ROUTE

    menu_map = {
        "menu_ssh": ("SSH", keyboards.get_ssh_menu_keyboard()),
        "menu_vmess": ("VMESS", keyboards.get_vmess_menu_keyboard()),
        "menu_vless": ("VLESS", keyboards.get_vless_menu_keyboard()),
        "menu_trojan": ("TROJAN", keyboards.get_trojan_menu_keyboard()),
        "menu_tools": ("TOOLS", keyboards.get_tools_menu_keyboard())
    }
    if command in menu_map:
        menu_name, keyboard = menu_map[command]
        await query.edit_message_text(f"{menu_name} PANEL MENU", reply_markup=keyboard)
        return ROUTE

    conv_starters = {
        "ssh_add": ("SSH Username:", SSH_GET_USERNAME),
        "vmess_add": ("VMESS Username:", VMESS_GET_USER),
        "vless_add": ("VLESS Username:", VLESS_GET_USER),
        "trojan_add": ("Trojan Username:", TROJAN_GET_USER)
    }
    if command in conv_starters:
        raw_text, state = conv_starters[command]
        await query.edit_message_text(f"➡️ Masukkan {raw_text}")
        return state

    if command == "ssh_renew":
        await query.edit_message_text(text="➡️ Silakan masukkan username akun SSH yang ingin diperpanjang:")
        return RENEW_SSH_GET_USERNAME
    elif command == "vmess_renew":
        await query.edit_message_text(text="➡️ Silakan masukkan username akun VMESS yang ingin diperpanjang:")
        return RENEW_VMESS_GET_USERNAME

    delete_starters = {
        "ssh_delete": ("SSH", DELETE_GET_USERNAME, "SSH username"),
        "vmess_delete": ("VMESS", DELETE_GET_USERNAME, "VMESS username"),
        "vless_delete": ("VLESS", DELETE_GET_USERNAME, "VLESS username"),
        "trojan_delete": ("TROJAN", DELETE_GET_USERNAME, "TROJAN username"),
    }
    if command in delete_starters:
        protocol, state, prompt_text = delete_starters[command]
        context.user_data['delete_protocol'] = protocol
        await query.edit_message_text(f"➡️ Masukkan {prompt_text} akun yang ingin dihapus:")
        return state

    trial_starters = {
        "ssh_trial": ("SSH", TRIAL_CREATE_SSH),
        "vmess_trial": ("VMESS", TRIAL_CREATE_VMESS),
        "vless_trial": ("VLESS", TRIAL_CREATE_VLESS),
        "trojan_trial": ("TROJAN", TRIAL_CREATE_TROJAN),
    }
    if command in trial_starters:
        protocol_name, state = trial_starters[command]
        await query.edit_message_text(f"➡️ Masukkan durasi (hari) untuk akun Trial {protocol_name}:")
        return state

    if command == "ssh_list" or command == "ssh_config_user":
        await ssh_list_accounts(update, context)
        return SSH_SELECT_ACCOUNT
    elif command == "vmess_list":
        await vmess_list_accounts(update, context)
        return VMESS_SELECT_ACCOUNT
    elif command == "vless_list":
        await vless_list_accounts(update, context)
        return ROUTE
    elif command == "trojan_list":
        await trojan_list_accounts(update, context)
        return ROUTE

    if command == "menu_running":
        await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/check_status_for_bot.sh'], "Status Layanan:")
        return ROUTE
    elif command == "menu_restart":
        await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/restart_for_bot.sh'], "Restart Layanan:")
        return ROUTE
    elif command == "reboot_server":
        context.user_data['action_to_confirm'] = 'reboot'
        await query.edit_message_text(
            "PERINGATAN!\n\nServer akan reboot dan bot akan berhenti sementara. Lanjutkan?",
            reply_markup=keyboards.get_confirmation_keyboard()
        )
        return ROUTE
    elif command == "trial_cleanup":
        await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/trial_cleanup.sh'], "Trial Cleanup:")
        return ROUTE

    elif command in ["confirm_proceed", "cancel_action"]:
        action = context.user_data.pop('action_to_confirm', None)
        if command == "confirm_proceed":
            if action == 'reboot':
                await query.edit_message_text("⏳ Server akan reboot dalam beberapa detik...", reply_markup=keyboards.get_back_to_menu_keyboard())
                try:
                    subprocess.Popen(['sudo', 'reboot'])
                except Exception as e:
                    await handle_script_error(update, context, e)
            elif action == 'restore':
                await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/restore_for_bot.sh'], "Proses Restore:")
            else:
                await query.edit_message_text("Aksi konfirmasi tidak dikenal atau sudah kadaluarsa.", reply_markup=keyboards.get_back_to_menu_keyboard())
        elif command == "cancel_action":
            await query.edit_message_text("Operasi dibatalkan.", reply_markup=keyboards.get_back_to_menu_keyboard())
        return ROUTE

    logger.warning(f"Unhandled callback query: {command} in route_handler.")
    await query.edit_message_text(f"Fitur {command} belum diimplementasikan atau tidak dikenal.", reply_markup=keyboards.get_back_to_menu_keyboard())
    return ROUTE

async def run_script_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, script_command: list, success_message: str):
    target_message = update.callback_query.message if update.callback_query else update.message

    processing_text = "⏳ Sedang memproses, mohon tunggu..."
    if update.callback_query and target_message.text:
        try:
            await target_message.edit_text(processing_text)
        except Exception:
            await update.effective_chat.send_message(processing_text)
    else:
        await target_message.reply_text(processing_text)

    try:
        p = subprocess.run(script_command, capture_output=True, text=True, check=True, timeout=60)
        output = p.stdout.strip()

        if output:
            response_text = f"✅ {success_message}\n\n{output}"
        else:
            response_text = f"✅ {success_message}\n\nOperasi selesai, tidak ada output spesifik."

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response_text,
            reply_markup=keyboards.get_back_to_menu_keyboard()
        )
        if update.callback_query:
            await target_message.delete()

    except Exception as e:
        await handle_script_error(update, context, e)

# --- SSH Creation Handlers ---
async def send_script_output(update: Update, context: ContextTypes.DEFAULT_TYPE, script_command: list):
    try:
        p = subprocess.run(script_command, capture_output=True, text=True, check=True, timeout=30)
        await update.message.reply_text(p.stdout.strip(), reply_markup=keyboards.get_back_to_menu_keyboard())
    except Exception as e:
        await handle_script_error(update, context, e)

async def ssh_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text("➡️ Masukkan Password:")
    return SSH_GET_PASSWORD

async def ssh_get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    await update.message.reply_text("➡️ Masukkan Durasi (hari):")
    return SSH_GET_DURATION

async def ssh_get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif. Silakan coba lagi.")
        return SSH_GET_DURATION
    context.user_data['duration'] = update.message.text
    await update.message.reply_text("➡️ Masukkan Limit IP:")
    return SSH_GET_IP_LIMIT

async def ssh_get_ip_limit_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) < 1:
        await update.message.reply_text("❌ Limit IP harus berupa angka positif. Silakan coba lagi.")
        return SSH_GET_IP_LIMIT
    context.user_data['ip_limit'] = update.message.text
    await update.message.reply_text("⏳ Membuat akun SSH...")
    ud = context.user_data
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_ssh.sh', ud['username'], ud['password'], ud['duration'], ud['ip_limit']])
    context.user_data.clear()
    return ROUTE

async def renew_ssh_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text
    context.user_data['renew_username'] = username
    await update.message.reply_text(
        f"✅ Username: {username}\n\n"
        "➡️ Sekarang, masukkan durasi perpanjangan (misal: 30 untuk 30 hari)."
    )
    return RENEW_SSH_GET_DURATION

async def renew_ssh_get_duration_and_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = update.message.text
    username = context.user_data.get('renew_username')
    if not duration.isdigit() or int(duration) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif. Silakan coba lagi.")
        return RENEW_SSH_GET_DURATION
    await update.message.reply_text("⏳ Sedang memproses perpanjangan, mohon tunggu...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_renew_ssh.sh', username, duration, str(update.effective_user.id)])
    context.user_data.clear()
    return ROUTE

# --- VMESS Renew Handlers ---
async def renew_vmess_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text
    context.user_data['renew_username'] = username
    await update.message.reply_text(
        f"✅ Username: {username}\n\n"
        "➡️ Sekarang, masukkan durasi perpanjangan (misal: 30 untuk 30 hari)."
    )
    return RENEW_VMESS_GET_DURATION

async def renew_vmess_get_duration_and_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = update.message.text
    username = context.user_data.get('renew_username')
    if not duration.isdigit() or int(duration) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif. Silakan coba lagi.")
        return RENEW_VMESS_GET_DURATION
    await update.message.reply_text("⏳ Sedang memproses perpanjangan VMESS, mohon tunggu...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_renew_vmess.sh', username, duration, str(update.effective_user.id)])
    context.user_data.clear()
    return ROUTE

# --- SSH List Accounts ---
async def ssh_list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        p = subprocess.run(['sudo', '/opt/hokage-bot/list_ssh_users.sh'], capture_output=True, text=True, check=True, timeout=30)
        script_output = p.stdout.strip()
    except Exception as e:
        await handle_script_error(update, context, e)
        return ROUTE
    if "NO_CLIENTS" in script_output:
        await query.edit_message_text("ℹ️ Belum ada akun SSH yang terdaftar di sistem.", reply_markup=keyboards.get_back_to_menu_keyboard())
        return ROUTE

    await query.edit_message_text(script_output)
    return SSH_SELECT_ACCOUNT

async def ssh_select_account_and_show_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    if user_input == '0':
        await update.message.reply_text("Dibatalkan.", reply_markup=keyboards.get_main_menu_keyboard())
        context.user_data.clear()
        return ROUTE

    await update.message.reply_text(f"⏳ Mengambil konfigurasi untuk akun nomor {user_input}...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/get_ssh_config.sh', user_input])
    context.user_data.clear()
    return ROUTE

# --- Trial Handlers (DIKEMBALIKAN) ---
async def create_ssh_trial_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = update.message.text
    if not duration.isdigit() or int(duration) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return TRIAL_CREATE_SSH
    await update.message.reply_text("⏳ Membuat akun Trial SSH...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_trial_ssh.sh', duration])
    return ConversationHandler.END

async def create_vmess_trial_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Karena main.py menggunakan filter.ALL, kita asumsikan durasi default
    duration = "1"
    await update.message.reply_text("⏳ Membuat akun Trial VMESS...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_trial_vmess.sh', duration])
    return ConversationHandler.END

async def create_vless_trial_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = update.message.text
    if not duration.isdigit() or int(duration) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return TRIAL_CREATE_VLESS
    await update.message.reply_text("⏳ Membuat akun Trial VLESS...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_trial_vless.sh', duration])
    return ConversationHandler.END

async def create_trojan_trial_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = update.message.text
    if not duration.isdigit() or int(duration) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return TRIAL_CREATE_TROJAN
    await update.message.reply_text("⏳ Membuat akun Trial TROJAN...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_trial_trojan.sh', duration])
    return ConversationHandler.END

# --- VMESS Handlers ---
async def vmess_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['user'] = update.message.text
    await update.message.reply_text("➡️ Masukkan Durasi (hari):")
    return VMESS_GET_DURATION

async def vmess_get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return VMESS_GET_DURATION
    context.user_data['duration'] = update.message.text
    ud = context.user_data
    await update.message.reply_text("⏳ Membuat akun VMESS...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_vmess_user.sh', ud['user'], ud['duration']])
    context.user_data.clear()
    return ROUTE

async def vmess_list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        p = subprocess.run(['sudo', '/opt/hokage-bot/list_vmess_users.sh'], capture_output=True, text=True, check=True, timeout=30)
        script_output = p.stdout.strip()
    except Exception as e:
        await handle_script_error(update, context, e)
        return ROUTE
    if "NO_CLIENTS" in script_output:
        await query.edit_message_text("ℹ️ Belum ada akun VMESS yang terdaftar.", reply_markup=keyboards.get_back_to_menu_keyboard())
        return ROUTE

    await query.edit_message_text(script_output)
    return VMESS_SELECT_ACCOUNT

async def vmess_select_account_and_show_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    if user_input == '0':
        await update.message.reply_text("Dibatalkan.", reply_markup=keyboards.get_main_menu_keyboard())
        context.user_data.clear()
        return ROUTE

    await update.message.reply_text(f"⏳ Mengambil konfigurasi untuk akun nomor {user_input}...")
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/get_vmess_config.sh', user_input])
    context.user_data.clear()
    return ROUTE

# --- VLESS Handlers ---
async def vless_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['user'] = update.message.text
    await update.message.reply_text("➡️ Masukkan durasi akun VLESS (hari):")
    return VLESS_GET_DURATION

async def vless_get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return VLESS_GET_DURATION
    context.user_data['duration'] = update.message.text
    await update.message.reply_text("➡️ Masukkan batas IP untuk akun VLESS:")
    return VLESS_GET_IP_LIMIT

async def vless_get_ip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) < 1:
        await update.message.reply_text("❌ Batas IP harus berupa angka positif.")
        return VLESS_GET_IP_LIMIT
    context.user_data['ip_limit'] = update.message.text
    await update.message.reply_text("➡️ Masukkan kuota GB untuk akun VLESS:")
    return VLESS_GET_QUOTA

async def vless_get_quota_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) < 0:
        await update.message.reply_text("❌ Kuota GB harus berupa angka.")
        return VLESS_GET_QUOTA
    context.user_data['quota_gb'] = update.message.text
    await update.message.reply_text("⏳ Membuat akun VLESS...")
    ud = context.user_data
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_vless_user.sh', ud['user'], ud['duration'], ud['ip_limit'], ud['quota_gb']])
    context.user_data.clear()
    return ROUTE

async def vless_list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Mengambil daftar akun VLESS...")
    await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/list_vless_users.sh'], "Daftar Akun VLESS")
    return ROUTE

# --- TROJAN Handlers ---
async def trojan_get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['user'] = update.message.text
    await update.message.reply_text("➡️ Masukkan durasi akun TROJAN (hari):")
    return TROJAN_GET_DURATION

async def trojan_get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) <= 0:
        await update.message.reply_text("❌ Durasi harus berupa angka positif.")
        return TROJAN_GET_DURATION
    context.user_data['duration'] = update.message.text
    await update.message.reply_text("➡️ Masukkan batas IP untuk akun TROJAN:")
    return TROJAN_GET_IP_LIMIT

async def trojan_get_ip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) < 1:
        await update.message.reply_text("❌ Batas IP harus berupa angka positif.")
        return TROJAN_GET_IP_LIMIT
    context.user_data['ip_limit'] = update.message.text
    await update.message.reply_text("➡️ Masukkan kuota GB untuk akun TROJAN:")
    return TROJAN_GET_QUOTA

async def trojan_get_quota_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.text.isdigit() or int(update.message.text) < 0:
        await update.message.reply_text("❌ Kuota GB harus berupa angka.")
        return TROJAN_GET_QUOTA
    context.user_data['quota_gb'] = update.message.text
    await update.message.reply_text("⏳ Membuat akun TROJAN...")
    ud = context.user_data
    await send_script_output(update, context, ['sudo', '/opt/hokage-bot/create_trojan_user.sh', ud['user'], ud['duration'], ud['ip_limit'], ud['quota_gb']])
    context.user_data.clear()
    return ROUTE

async def trojan_list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Mengambil daftar akun TROJAN...")
    await run_script_and_reply(update, context, ['sudo', '/opt/hokage-bot/list_trojan_users.sh'], "Daftar Akun TROJAN")
    return ROUTE

# --- Delete Handlers ---
async def delete_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username_to_delete = update.message.text
    context.user_data['username_to_delete'] = username_to_delete
    protocol = context.user_data.get('delete_protocol', 'Akun')
    await update.message.reply_text(
        f"Anda yakin ingin menghapus akun {protocol} dengan username {username_to_delete}?",
        reply_markup=keyboards.get_confirmation_keyboard()
    )
    return DELETE_CONFIRMATION

async def delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    username_to_delete = context.user_data.get('username_to_delete')
    protocol = context.user_data.get('delete_protocol')

    if query.data == "confirm_proceed":
        if not username_to_delete or not protocol:
            await query.edit_message_text("❌ Informasi akun tidak lengkap.", reply_markup=keyboards.get_back_to_menu_keyboard())
            context.user_data.clear()
            return ROUTE

        await query.edit_message_text(f"⏳ Sedang menghapus akun {protocol}...")
        try:
            script_map = {
                'ssh': '/opt/hokage-bot/delete-ssh.sh',
                'vmess': '/opt/hokage-bot/delete_vmess_user.sh',
                'vless': '/opt/hokage-bot/delete_vless_user.sh',
                'trojan': '/opt/hokage-bot/delete_trojan_user.sh'
            }
            script_path = script_map.get(protocol.lower())
            if not script_path:
                raise ValueError(f"Protokol {protocol} tidak didukung.")

            p = subprocess.run(['sudo', script_path, username_to_delete], capture_output=True, text=True, check=True, timeout=30)
            await query.edit_message_text(p.stdout.strip(), reply_markup=keyboards.get_back_to_menu_keyboard())
        except Exception as e:
            await handle_script_error(update, context, e)
    else:
        await query.edit_message_text("Operasi penghapusan dibatalkan.", reply_markup=keyboards.get_back_to_menu_keyboard())

    context.user_data.clear()
    return ROUTE

# --- Conversation Control ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_chat.send_message("❌ Operasi dibatalkan.", reply_markup=keyboards.get_main_menu_keyboard())
    return ConversationHandler.END

async def back_to_menu_from_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data:
        context.user_data.clear()
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Dibatalkan, kembali ke menu utama.", reply_markup=keyboards.get_main_menu_keyboard())
    return ROUTE
# --- TAMBAHAN: HANDLERS UNTUK PEMBELIAN PAKET DATA XL ---

async def start_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai alur pembelian, meminta nomor HP."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Silakan masukkan nomor XL/Axis yang akan diisi (contoh: 087812345678)."
    )
    return PURCHASE_ASK_PHONE_NUMBER

async def ask_package(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima nomor HP, lalu menampilkan daftar paket."""
    phone_number = update.message.text.strip()
    
    # Validasi sederhana nomor HP
    if not (phone_number.startswith('08') and len(phone_number) > 9 and phone_number.isdigit()):
        await update.message.reply_text("Format nomor salah. Gunakan awalan 08 dan pastikan hanya angka. Silakan coba lagi.")
        return PURCHASE_ASK_PHONE_NUMBER

    context.user_data['phone_number'] = phone_number
    await update.message.reply_text("⏳ Mengambil daftar paket, mohon tunggu...")
    
    # Ambil paket dari DB
    packages = database.get_all_packages()
    if not packages:
        await update.message.reply_text("Maaf, tidak dapat mengambil daftar paket saat ini. Coba lagi nanti.")
        return ConversationHandler.END

    keyboard_buttons = []
    text = "Silakan pilih paket yang Anda inginkan:\n"
    for pkg in packages[:25]: # Batasi jumlah tombol agar tidak overload
        harga = f"Rp{pkg['harga_final']:,}".replace(',', '.')
        button_text = f"{pkg['package_name']} - {harga}"
        keyboard_buttons.append([InlineKeyboardButton(button_text, callback_data=f"pkg_{pkg['package_code']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(text, reply_markup=reply_markup)
    
    return PURCHASE_ASK_PACKAGE

async def ask_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima pilihan paket, lalu meminta konfirmasi akhir."""
    query = update.callback_query
    await query.answer()
    
    package_code = query.data.replace('pkg_', '')
    context.user_data['package_code'] = package_code
    
    await query.edit_message_text("⏳ Memeriksa saldo dan detail paket...")

    # Ambil detail paket & user dari DB
    pkg_details = database.get_package_details(package_code)
    # Penting: Sesuaikan fungsi get_user_balance agar bisa mencari berdasarkan telegram_user_id
    user_data = database.get_user_balance(update.effective_user.id)
    
    if not pkg_details or not user_data or user_data.get('balance') is None:
        await query.edit_message_text("Terjadi kesalahan saat mengambil data pengguna atau paket. Pastikan akun Anda terhubung.")
        return ConversationHandler.END
        
    harga_paket = int(pkg_details['harga_final'])
    context.user_data['harga_paket'] = harga_paket
    # harga_kmsp mungkin NULL jika tidak ada di tabel harga_paket, beri nilai default 0
    context.user_data['harga_kmsp'] = int(pkg_details.get('harga_kmsp') or 0)

    if user_data['balance'] < harga_paket:
        await query.edit_message_text(
            f"Maaf, saldo Anda (Rp{user_data['balance']:,}) tidak cukup untuk membeli paket ini (Rp{harga_paket:,}).".replace(',', '.'),
            reply_markup=keyboards.get_back_to_menu_keyboard()
        )
        return ConversationHandler.END

    # Tampilkan ringkasan untuk konfirmasi
    phone_number = context.user_data['phone_number']
    saldo_sekarang_str = f"Rp{user_data['balance']:,}".replace(',', '.')
    harga_paket_str = f"Rp{harga_paket:,}".replace(',', '.')
    saldo_sisa_str = f"Rp{user_data['balance'] - harga_paket:,}".replace(',', '.')

    text = (
        f"🔔 *Konfirmasi Pembelian*\n\n"
        f"📞 *Nomor Tujuan:* `{phone_number}`\n"
        f"📦 *Paket:* {pkg_details['package_name']}\n"
        f"💰 *Harga:* {harga_paket_str}\n\n"
        f"💵 *Saldo Anda:* {saldo_sekarang_str}\n"
        f"📉 *Saldo Setelah Beli:* {saldo_sisa_str}\n\n"
        f"Anda yakin ingin melanjutkan?"
    )
    
    # Gunakan keyboard konfirmasi khusus pembelian
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_purchase_confirmation_keyboard(),
        parse_mode='Markdown'
    )
    
    return PURCHASE_CONFIRM

async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Langkah terakhir: memproses pembelian ke API KMSP dan mencatat ke DB."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("✅ Konfirmasi diterima. Memproses pembelian Anda ke server... Mohon tunggu.")

    # Ambil semua data yang tersimpan dari context
    user_id = update.effective_user.id
    phone_number = context.user_data['phone_number']
    package_code = context.user_data['package_code']
    harga_paket = context.user_data['harga_paket']
    harga_kmsp = context.user_data['harga_kmsp']
    
    # Panggil fungsi API. Asumsi metode bayar 'DANA', bisa dibuat dinamis jika perlu.
    result = kmsp_api.purchase_package(package_code, phone_number, 'DANA', harga_kmsp)

    user_info = database.get_user_balance(user_id)
    pkg_details = database.get_package_details(package_code)

    if result and result.get('status'):
        # Transaksi SUKSES dari sisi API
        new_balance = user_info['balance'] - harga_paket
        database.update_user_balance(user_info['username'], new_balance)
        
        success_message = result.get('message', 'Pembelian sukses!')
        trx_id = result.get('data', {}).get('trx_id', 'N/A')
        await query.edit_message_text(f"✅ *BERHASIL!*\n\n{success_message}\n*Transaction ID:* `{trx_id}`", parse_mode='Markdown', reply_markup=keyboards.get_back_to_menu_keyboard())
        
        status_log = 'success'
    else:
        # Transaksi GAGAL dari sisi API
        error_message = result.get('message', 'Terjadi kesalahan tidak diketahui dari server.')
        await query.edit_message_text(f"❌ *GAGAL!*\n\nPesan: {error_message}", reply_markup=keyboards.get_back_to_menu_keyboard())
        status_log = 'error'

    # Log transaksi ke DB (baik sukses maupun gagal)
    log_data = {
        'wid': 'WID' + str(uuid.uuid4().int)[:10],
        'tid': result.get('data', {}).get('trx_id', 'TID' + str(uuid.uuid4().int)[:10]),
        'user': user_info.get('username', 'telegram_user'),
        'code': package_code,
        'name': pkg_details['package_name'],
        'data': phone_number,
        'note': result.get('message', 'No message from API'),
        'price': harga_paket,
        'status': status_log,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    database.log_transaction(log_data)
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan alur pembelian."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Pembelian dibatalkan.", reply_markup=keyboards.get_main_menu_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- AKHIR TAMBAHAN ---


# --- Conversation Control ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_chat.send_message("❌ Operasi dibatalkan.", reply_markup=keyboards.get_main_menu_keyboard())
    return ConversationHandler.END

async def back_to_menu_from_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data:
        context.user_data.clear()
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Dibatalkan, kembali ke menu utama.", reply_markup=keyboards.get_main_menu_keyboard())
    return ROUTE

# --- TAMBAHAN: DEFINISI CONVERSATION HANDLER BARU UNTUK PEMBELIAN XL ---
# Variabel ini akan diimpor oleh main.py
purchase_xl_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_purchase, pattern='^purchase_xl_start$')],
    states={
        PURCHASE_ASK_PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_package)],
        PURCHASE_ASK_PACKAGE: [CallbackQueryHandler(ask_confirmation, pattern='^pkg_')],
        PURCHASE_CONFIRM: [
            CallbackQueryHandler(process_purchase, pattern='^confirm_purchase_yes$'),
            CallbackQueryHandler(cancel_purchase, pattern='^confirm_purchase_no$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel)], # Menggunakan fungsi cancel yang sudah ada
    per_user=True, # Data terpisah untuk setiap user
    conversation_timeout=300 # Otomatis batal setelah 5 menit tidak aktif
)
# --- AKHIR TAMBAHAN ---
