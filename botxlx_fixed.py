import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.helpers import escape_markdown
import requests
from datetime import datetime, timedelta, timezone
import json
from datetime import datetime, timedelta
import os
import re
import signal
import sys
import asyncio
import math
import html
import base64
import traceback 
import uuid 
import random
import sqlite3
bot_start_time = datetime.now()

DB_FILE = 'bot_database.sqlite'


def inisialisasi_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
        balance INTEGER DEFAULT 0, accounts TEXT DEFAULT '{}',
        transactions TEXT DEFAULT '[]', selected_hesdapkg_ids TEXT DEFAULT '[]',
        selected_30h_pkg_ids TEXT DEFAULT '[]', is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0, phone_number TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_packages (
        code TEXT PRIMARY KEY, name TEXT, price INTEGER, description TEXT,
        payment_methods TEXT, ewallet_fee INTEGER DEFAULT 0
    )''')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS blocked_users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()
    logging.info("Database SQLite berhasil diinisialisasi.")

def simpan_data_ke_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for user_id_str, details in user_data["registered_users"].items():
        cursor.execute('''
        INSERT OR REPLACE INTO users (id, first_name, username, balance, accounts, transactions, selected_hesdapkg_ids, selected_30h_pkg_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(user_id_str), details.get('first_name'), details.get('username'),
            details.get('balance', 0), json.dumps(details.get('accounts', {})),
            json.dumps(details.get('transactions', [])), json.dumps(details.get('selected_hesdapkg_ids', [])),
            json.dumps(details.get('selected_30h_pkg_ids', []))
        ))
    cursor.execute("DELETE FROM blocked_users")
    if user_data.get("blocked_users"):
        cursor.executemany("INSERT INTO blocked_users (user_id) VALUES (?)", [(uid,) for uid in user_data["blocked_users"]])
    conn.commit()
    conn.close()
    logging.info("Data berhasil disimpan ke SQLite.")

def muat_data_dari_db():
    global user_data
    user_data = {"registered_users": {}, "blocked_users": [], "custom_packages": {}}
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # PERBAIKAN: Menggunakan nama kolom yang benar ('id')
    cursor.execute("SELECT id, first_name, username, balance, accounts, transactions, selected_hesdapkg_ids, selected_30h_pkg_ids FROM users")
    for row in cursor.fetchall():
        user_id_str = str(row[0])
        user_data["registered_users"][user_id_str] = {
            "first_name": row[1], "username": row[2], "balance": row[3],
            "accounts": json.loads(row[4] or '{}'),
            "transactions": json.loads(row[5] or '[]'),
            "selected_hesdapkg_ids": json.loads(row[6] or '[]'),
            "selected_30h_pkg_ids": json.loads(row[7] or '[]')
        }
    cursor.execute("SELECT user_id FROM blocked_users")
    user_data["blocked_users"] = [row[0] for row in cursor.fetchall()]
    conn.close()
    logging.info(f"Data dari SQLite berhasil dimuat. Total {len(user_data['registered_users'])} user.")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("botxl.log"),
        logging.StreamHandler()
    ]
)

                  
KMSP_API_KEY = os.getenv("XL_API_KEY", "c7d49152-51a3-4cf4-b696-af8bd60ad2d8")

HESDA_API_KEY = os.getenv("HESDA_API_KEY", "2iB0Qvvqaw85lCOvCy")
HESDA_USERNAME = os.getenv("HESDA_USERNAME", "ikbal192817@gmail.com")
HESDA_PASSWORD = os.getenv("HESDA_PASSWORD", "ayomasuk123")


ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1469244768"))
ADMIN_USERNAME = os.getenv("ADMIN_TELEGRAM_USERNAME", "hokagelegend1")
QRIS_STATIS = os.getenv("QRIS_STATIS", "00020101021226610016ID.CO.SHOPEE.WWW01189360091800221899870208221899870303UMI51440014ID.CO.QRIS.WWW0215ID10254101517530303UMI5204541153033605405125005802ID5909IST STORE6006SERANG61054211162070703A016304428D")

CUSTOM_PACKAGE_PRICES = {
    "XL_XC1PLUS1DISC_EWALLET": {"price_bot": 5000, "display_name": "XC 1+1GB DANA"},
    "XLUNLITURBOTIKTOK_DANA": {"price_bot": 200, "display_name": "ADD ON TIKTOK (DANA)"}, 
    "XLUNLITURBOVIU_DANA": {"price_bot": 200, "display_name": "ADD ON VIU (DANA)"}, 
    "XLUNLITURBOJOOXXC": {"price_bot": 200, "display_name": "ADD ON JOOX (DANA)"}, 
    "XLUNLITURBONETFLIXXC": {"price_bot": 200, "display_name": "ADD ON NETFLIX (DANA)"}, 
    "XLUNLITURBOHPREMIUM7H": {"price_bot": 200, "display_name": "PREMIUM 7H (DANA)"}, 
    "XLUNLITURBOHSUPER7H": {"price_bot": 200, "display_name": "SUPER 7H (DANA)"}, 
    "XLUNLITURBOHBASIC7H": {"price_bot": 200, "display_name": "BASIC 7H (DANA)"}, 
    "XLUNLITURBOHSTANDARD7H": {"price_bot": 200, "display_name": "STANDAR 7H (DANA)"}, 
    "XLUNLITURBOPREMIUMXC": {"price_bot": 200, "display_name": "ADD ON PREMIUM (DANA)"}, 
    "XLUNLITURBOSUPERXC": {"price_bot": 200, "display_name": "ADD ON SUPER (DANA)"}, 
    "XLUNLITURBOBASICXC": {"price_bot": 200, "display_name": "ADD ON BASIC (DANA)"}, 
    "XLUNLITURBOSTANDARDXC": {"price_bot": 200, "display_name": "ADD ON STANDAR (DANA)"}, 
   "WjNMaVEyR0NoNG5SdUhHYWFLbU9RUQ": {"price_bot": 200, "display_name": "BYPAS BASIC"}, 
   "aCtmMVl2YldLZDcvRzhJNlQraTNZdw": {"price_bot": 200, "display_name": "BYPAS STANDARD"}, 
   "eUxzZE9Wa0dmdTdDT1RDeVFyOWJyZw": {"price_bot": 200, "display_name": "BYPAS SUPER"}, 
    "UzhmQk5zam53SUZReWJ3c0poZ0xaQQ": {"price_bot": 200, "display_name": "BYPAS PREMIUM"}, 
    "VlNxbzdGbDRtVnZHUmdwb284R2wzdw": {"price_bot": 200, "display_name": "BYPAS JOOX"}, 
    "SDNuUmJBbWEvMnZSVFRCcEtzQlBFZw": {"price_bot": 200, "display_name": "BYPAS YOUTUBE"}, 
    "MnFpMjJHaXhpU2pweUZ2WWRRM0tYZw": {"price_bot": 200, "display_name": "BYPAS NETFLIX"}, 
    "dlZJSi9kRC85U2tuc3ZaQkVmc1lkQQ": {"price_bot": 200, "display_name": "BYPAS TIKTOK"}, 
    "Tm8vcWtGQ01Kc3h1dlFFdGZqQ3FzUQ": {"price_bot": 200, "display_name": "BYPAS VIU"}, 
    "bStlR1JhcUkrZzlhYmdURWRMNUlaQQ": {"price_bot": 200, "display_name": "BYPAS BASIC 7H"}, 
    "VWM1ZWF0Nk1GQW9MRTEyajJnWFcrdw": {"price_bot": 200, "display_name": "BYPAS STANDARD 7H"}, 
    "N3IvV0NHUEtNUzV6ZlNYR0l0MTNuUQ": {"price_bot": 200, "display_name": "BYPAS PREMIUM 7H"}, 
    "c03be70fb3523ac2ac440966d3a5920e": {"price_bot": 5000, "display_name": "XCP 8GB DANA"}, 
    "bdb392a7aa12b21851960b7e7d54af2c": {"price_bot": 5000, "display_name": "XCP 8GB PULSA"}, 
    "XL_XC1PLUS1DISC_PULSA": {"price_bot": 5000, "display_name": "XC 1+1GB PULSA"}, 
    "XL_XC1PLUS1DISC_QRIS": {"price_bot": 5000, "display_name": "XC 1+1GB QRIS"}, 
    "c03be70fb3523ac2ac440966d3a5920e_QRIS": {"price_bot": 5000, "display_name": "XCP 8GB QRIS"}, 
    "XLUNLITURBOPREMIUMXC_PULSA": {"price_bot": 200, "display_name": "ADD ON PREMIUM (PULSA)"}, 
    "XLUNLITURBOSUPERXC_PULSA": {"price_bot": 200, "display_name": "ADD ON SUPER (PULSA)"}, 
    "XLUNLITURBOBASICXC_PULSA": {"price_bot": 200, "display_name": "ADD ON BASIC (PULSA)"}, 
    "XLUNLITURBOSTANDARDXC_PULSA": {"price_bot": 200, "display_name": "ADD ON STANDAR (PULSA)"}, 
    "XLUNLITURBOVIU_PULSA": {"price_bot": 200, "display_name": "ADD ON VIU (PULSA)"}, 
    "XLUNLITURBOTIKTOK_PULSA": {"price_bot": 200, "display_name": "ADD ON TIKTOK (PULSA)"}, 
    "XLUNLITURBONETFLIXXC_PULSA": {"price_bot": 200, "display_name": "ADD ON NETFLIX (PULSA)"}, 
    "XLUNLITURBOYOUTUBEXC_PULSA": {"price_bot": 200, "display_name": "ADD ON YOUTUBE (PULSA)"}, 
    "XLUNLITURBOJOOXXC_PULSA": {"price_bot": 200, "display_name": "ADD ON JOOX (PULSA)"}, 
    "XLUNLITURBOHPREMIUM7H_P": {"price_bot": 200, "display_name": "PREMIUM 7H (PULSA)"}, 
    "XLUNLITURBOHSUPER7H_P": {"price_bot": 200, "display_name": "SUPER 7H (PULSA)"}, 
    "XLUNLITURBOHBASIC7H_P": {"price_bot": 200, "display_name": "BASIC 7H (PULSA)"}, 
    "XLUNLITURBOHSTANDARD7H_P": {"price_bot": 200, "display_name": "STANDAR 7H (PULSA)"}, 
    "XLUNLITURBOVIDIO_PULSA": {"price_bot": 3000, "display_name": "VIDIO XL (PULSA)"}, 
    "XLUNLITURBOVIDIO_QRIS": {"price_bot": 3000, "display_name": "VIDIO XL (QRIS)"}, 
    "XLUNLITURBOVIDIO_DANA": {"price_bot": 3000, "display_name": "VIDIO XL (DANA)"}, 
    "XLUNLITURBOIFLIXXC_DANA": {"price_bot": 3000, "display_name": "IFLIX XL (DANA)"}, 
    "XLUNLITURBOIFLIXXC_PULSA": {"price_bot": 3000, "display_name": "IFLIX XL (PULSA)"}, 
    "XLUNLITURBOIFLIXXC_QRIS": {"price_bot": 3000, "display_name": "IFLIX XL (QRIS)"},
}

ADD_ON_SEQUENCE = [
    {"code": "XLUNLITURBOPREMIUMXC_PULSA", "name": "ADD ON PREMIUM"},
    {"code": "XLUNLITURBOSUPERXC_PULSA", "name": "ADD ON SUPER"},
    {"code": "XLUNLITURBOBASICXC_PULSA", "name": "ADD ON BASIC"},
    {"code": "XLUNLITURBOSTANDARDXC_PULSA", "name": "ADD ON STANDAR"},
    {"code": "XLUNLITURBOTIKTOK_PULSA", "name": "ADD ON TIKTOK"},
    {"code": "XLUNLITURBOVIU_PULSA", "name": "ADD ON VIU"},
    {"code": "XLUNLITURBOJOOXXC_PULSA", "name": "ADD ON JOX"},
    {"code": "XLUNLITURBONETFLIXXC_PULSA", "name": "ADD ON NETFLIX"},
    {"code": "XLUNLITURBOYOUTUBEXC_PULSA", "name": "ADD ON YOUTUBE"},
    {"code": "XLUNLITURBOHPREMIUM7H_P", "name": "PREMIUM 7H"},
    {"code": "XLUNLITURBOHSUPER7H_P", "name": "SUPER 7H"},
    {"code": "XLUNLITURBOHBASIC7H_P", "name": "BASIC 7H"},
    {"code": "XLUNLITURBOHSTANDARD7H_P", "name": "STANDAR 7H"},
]

XCP_8GB_PACKAGE = {"code": "c03be70fb3523ac2ac440966d3a5920e", "name": "XCP 8GB"}
XCP_8GB_PULSA_PACKAGE = {"code": "bdb392a7aa12b21851960b7e7d54af2c", "name": "XCP 8GB PULSA"}

HESDA_PACKAGES = [
    {"id": "WjNMaVEyR0NoNG5SdUhHYWFLbU9RUQ", "name": "BASIC", "price_bot": 200},
    {"id": "aCtmMVl2YldLZDcvRzhJNlQraTNZdw", "name": "STANDARD", "price_bot": 200},
    {"id": "eUxzZE9Wa0dmdTdDT1RDeVFyOWJyZw", "name": "SUPER", "price_bot": 200},
    {"id": "UzhmQk5zam53SUZReWJ3c0poZ0xaQQ", "name": "PREMIUM", "price_bot": 200},
    {"id": "VlNxbzdGbDRtVnZHUmdwb284R2wzdw", "name": "JOOX", "price_bot": 200},
    {"id": "SDNuUmJBbWEvMnZSVFRCcEtzQlBFZw", "name": "YOUTUBE", "price_bot": 200},
    {"id": "MnFpMjJHaXhpU2pweUZ2WWRRM0tYZw", "name": "NETFLIX", "price_bot": 200},
    {"id": "dlZJSi9kRC85U2tuc3ZaQkVmc1lkQQ", "name": "TIKTOK", "price_bot": 200},
    {"id": "Tm8vcWtGQ01Kc3h1dlFFdGZqQ3FzUQ", "name": "VIU", "price_bot": 200}, 
    {"id": "bStlR1JhcUkrZzlhYmdURWRMNUlaQQ", "name": "BASIC 7H", "price_bot": 200},
    {"id": "VWM1ZWF0Nk1GQW9MRTEyajJnWFcrdw", "name": "STANDARD 7H", "price_bot": 200},
    {"id": "N3IvV0NHUEtNUzV6ZlNYR0l0MTNuUQ", "name": "PREMIUM 7H", "price_bot": 200},
]

THIRTY_H_PACKAGES = [
    {"id": "XLUNLITURBOPREMIUMXC_PULSA", "name": "PREMIUM 30H", "price_bot": 200},
    {"id": "XLUNLITURBOSUPERXC_PULSA", "name": "SUPER 30H", "price_bot": 250},
    {"id": "XLUNLITURBOBASICXC_PULSA", "name": "BASIC 30H", "price_bot": 200},
    {"id": "XLUNLITURBOSTANDARDXC_PULSA", "name": "STANDARD 30H", "price_bot": 200},
    {"id": "XLUNLITURBONETFLIXXC_PULSA", "name": "NETFLIX", "price_bot": 200},
    {"id": "XLUNLITURBOTIKTOK_PULSA", "name": "TIKTOK", "price_bot": 200},
    {"id": "XLUNLITURBOJOOXXC_PULSA", "name": "JOOX", "price_bot": 200},
    {"id": "XLUNLITURBOVIU_PULSA", "name": "VIU", "price_bot": 200},
    {"id": "XLUNLITURBOYOUTUBEXC_PULSA", "name": "YOUTUBE", "price_bot": 200},
    {"id": "XLUNLITURBOHPREMIUM7H_P", "name": "PREMIUM 7H", "price_bot": 200},
    {"id": "XLUNLITURBOHSUPER7H_P", "name": "SUPER 7H", "price_bot": 200},
    {"id": "XLUNLITURBOHBASIC7H_P", "name": "BASIC 7H", "price_bot": 200},
    {"id": "XLUNLITURBOHSTANDARD7H_P", "name": "STANDARD 7H", "price_bot": 200},
]

MIN_BALANCE_FOR_PURCHASE = 5000
MIN_TOP_UP_AMOUNT = 5000

QRIS_FOLDER = "FOTO_QRIS"
QRIS_FILE_NAME = "qris.png"
QRIS_FILE_PATH = os.path.abspath(os.path.join(QRIS_FOLDER, QRIS_FILE_NAME))

MAX_ADDON_PURCHASE_RETRIES = 10
PACKAGES_PER_PAGE_ADMIN = 10
USERS_PER_PAGE_ADMIN = 15
TRANSACTIONS_PER_PAGE_ADMIN = 10
ADDON_BATCH_SIZE = 4

async def qris_expiration_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data['user_id']
    qris_message_id = job.data['qris_message_id']
    qris_photo_id = job.data['qris_photo_id']

    try:
        if qris_photo_id:
            await context.bot.delete_message(chat_id=user_id, message_id=qris_photo_id)
    except Exception as e:
        logging.warning(f"Gagal menghapus pesan foto QRIS {qris_photo_id} untuk user {user_id}: {e}")

    try:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=qris_message_id,
            text="⚠️ QRIS telah kedaluwarsa. Silakan buat permintaan pembelian baru jika Anda masih ingin membeli paket.",
            reply_markup=None
        )
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=user_id, message_id=qris_message_id) and None,
            30,
            data={'user_id': user_id, 'message_id': qris_message_id},
            name=f"delete_expired_qris_message_{user_id}_{qris_message_id}"
        )
    except Exception as e:
        logging.warning(f"Gagal mengedit atau menghapus pesan teks QRIS {qris_message_id} untuk user {user_id}: {e}")

def simpan_data_ke_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for user_id_str, details in user_data["registered_users"].items():
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, first_name, username, balance, accounts, transactions, selected_hesdapkg_ids, selected_30h_pkg_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(user_id_str),
            details.get('first_name', 'N/A'),
            details.get('username', 'N/A'),
            details.get('balance', 0),
            json.dumps(details.get('accounts', {})),
            json.dumps(details.get('transactions', [])),
            json.dumps(details.get('selected_hesdapkg_ids', [])),
            json.dumps(details.get('selected_30h_pkg_ids', []))
        ))
    
    cursor.execute("DELETE FROM blocked_users")
    if user_data["blocked_users"]:
        cursor.executemany("INSERT INTO blocked_users (user_id) VALUES (?)", [(uid,) for uid in user_data["blocked_users"]])

    cursor.execute("DELETE FROM custom_packages")
    if user_data["custom_packages"]:
        package_list = [
            (
                code, 
                details['name'], 
                details['price'], 
                details.get('description', ''), 
                json.dumps(details.get('payment_methods', []))
            ) 
            for code, details in user_data["custom_packages"].items()
        ]
        cursor.executemany("INSERT INTO custom_packages (code, name, price, description, payment_methods) VALUES (?, ?, ?, ?, ?)", package_list)

    conn.commit()
    conn.close()
    logging.info("Data berhasil disimpan ke SQLite.")

def muat_data_dari_db():
    global user_data
    user_data = {
        "registered_users": {},
        "blocked_users": [],
        "custom_packages": {}
    }
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        user_id_str = str(row[0])
        user_data["registered_users"][user_id_str] = {
            "first_name": row[1],
            "username": row[2],
            "balance": row[3],
            "accounts": json.loads(row[4] or '{}'),
            "transactions": json.loads(row[5] or '[]'),
            "selected_hesdapkg_ids": json.loads(row[6] or '[]'),
            "selected_30h_pkg_ids": json.loads(row[7] or '[]')
        }

    cursor.execute("SELECT user_id FROM blocked_users")
    user_data["blocked_users"] = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT code, name, price, description, payment_methods FROM custom_packages")
    for row in cursor.fetchall():
        user_data["custom_packages"][row[0]] = {
            "name": row[1],
            "price": row[2],
            "description": row[3],
            "payment_methods": json.loads(row[4] or '[]')
        }
    
    conn.close()
    logging.info(f"📂 Data dari SQLite berhasil dimuat. Total {len(user_data['registered_users'])} user.")

user_data = {}
package_info = {}
custom_package_display_info = {}
package_pages = {}
bot_messages = {}
login_counter = {}

inisialisasi_database()
muat_data_dari_db()

XUTS_PACKAGE_CODE = "XLUNLITURBOSUPERXC_PULSA" 
XC1PLUS1GB_PULSA_CODE = "XL_XC1PLUS1DISC_PULSA"
XC1PLUS1GB_DANA_CODE = "XL_XC1PLUS1DISC_EWALLET"
XC1PLUS1GB_QRIS_CODE = "XL_XC1PLUS1DISC_QRIS" 

XUTP_INITIAL_PACKAGE_CODE = "XLUNLITURBOPREMIUMXC_PULSA"
XCP_8GB_DANA_CODE_FOR_XUTP = "c03be70fb3523ac2ac440966d3a5920e" 
XCP_8GB_PULSA_CODE_FOR_XUTP = "bdb392a7aa12b21851960b7e7d54af2c" 
XCP_8GB_QRIS_CODE_FOR_XUTP = "c03be70fb3523ac2ac440966d3a5920e_QRIS" 

def calculate_total_successful_transactions():
    count = 0
    all_users = user_data.get("registered_users", {})
    for user_id, details in all_users.items():
        transactions = details.get("transactions", [])
        for tx in transactions:
            if tx.get("status") == "Berhasil":
                count += 1
    return count

async def run_automatic_xcs_addon_flow(update, context):
    user_id = update.effective_user.id
    automatic_xcs_flow_state = context.user_data.get('automatic_xcs_flow_state')

    if not automatic_xcs_flow_state:
        if context.user_data.get('overall_status_message_id'):
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=context.user_data['overall_status_message_id'])
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan status lama: {e}")
            del context.user_data['overall_status_message_id']
        await context.bot.send_message(user_id, "Sesi pembelian otomatis XCS ADD ON tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

                                
    phone = automatic_xcs_flow_state['phone']
    access_token = automatic_xcs_flow_state['access_token']
    payment_method_xcp_8gb = automatic_xcs_flow_state['payment_method_xcp_8gb']
    
    automatic_xcs_flow_state.setdefault('addons_to_process', [])
    automatic_xcs_flow_state.setdefault('current_addon_index', 0)
    automatic_xcs_flow_state.setdefault('addon_pending_retry_count', 0)
    automatic_xcs_flow_state.setdefault('addon_results', {})
    
                                                               
    automatic_xcs_flow_state.setdefault('failed_attempts_for_reprocess', {})
    automatic_xcs_flow_state.setdefault('current_reprocess_id_index', 0)
    automatic_xcs_flow_state.setdefault('reprocess_attempts_counter', {})
    automatic_xcs_flow_state.setdefault('flow_has_waited', False)
    automatic_xcs_flow_state.setdefault('reprocessing_countdown_initiated', False)
    automatic_xcs_flow_state.setdefault('reprocessing_pass_count', 1)
    automatic_xcs_flow_state.setdefault('xcp_8gb_completed', False)
    
                                                                                
    automatic_xcs_flow_state.setdefault('reprocessing_queue', [])

                       
    MAX_REPROCESSING_PASSES = 2                                
    
                         
    addons_to_process = automatic_xcs_flow_state['addons_to_process']
    current_addon_index = automatic_xcs_flow_state['current_addon_index']
    addon_pending_retry_count = automatic_xcs_flow_state['addon_pending_retry_count']
    addon_results = automatic_xcs_flow_state['addon_results']
    failed_attempts_for_reprocess = automatic_xcs_flow_state['failed_attempts_for_reprocess']
    current_reprocess_id_index = automatic_xcs_flow_state['current_reprocess_id_index']
    reprocess_attempts_counter = automatic_xcs_flow_state['reprocess_attempts_counter']
    status_message_id = automatic_xcs_flow_state.setdefault('overall_status_message_id', None)
    
                                                              
    reprocessing_queue = automatic_xcs_flow_state['reprocessing_queue']

                                    
    current_status_text = ""
    
    if current_addon_index < len(addons_to_process):
                                      
        addon_info_current = next((pkg for pkg in ADD_ON_SEQUENCE if pkg['code'] == addons_to_process[current_addon_index]), None)
        current_addon_name_for_display = addon_info_current['name'] if addon_info_current else "Paket Tidak Dikenal"
        current_status_text = (
            f"Melanjutkan alur XCS ADD ON otomatis untuk *{phone}*...\n"
            f"📦 Memproses paket awal: *{current_addon_name_for_display}* "
            f"({current_addon_index + 1} dari {len(addons_to_process)})"
        )
                                                                                             
    elif reprocessing_queue and current_reprocess_id_index < len(reprocessing_queue):
                                                                
        unique_failure_id_to_retry = reprocessing_queue[current_reprocess_id_index]
        failure_details = failed_attempts_for_reprocess.get(unique_failure_id_to_retry)                                
        
        if failure_details:
            current_addon_name_for_display = failure_details['package_name']
            current_reprocess_attempt_count = reprocess_attempts_counter.get(unique_failure_id_to_retry, 0)
            MAX_REPROCESS_ATTEMPTS = 3
            current_pass = automatic_xcs_flow_state.get('reprocessing_pass_count', 1)
            current_status_text = (
                f"✅ Selesai memproses semua paket awal.\n"
                f"🔁 Mencoba ulang paket gagal (Putaran {current_pass}/{MAX_REPROCESSING_PASSES}):\n"
                f"   Paket: *{current_addon_name_for_display}* ({current_reprocess_id_index + 1} dari {len(reprocessing_queue)})\n"                   
                f"   (Percobaan ke-{current_reprocess_attempt_count + 1} / Maks {MAX_REPROCESS_ATTEMPTS})"
            )
        else:
                                                                                         
            current_status_text = f"Melewatkan item yang tidak valid di antrean..."
            automatic_xcs_flow_state['current_reprocess_id_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return
            
    else:
                                             
        current_status_text = "✅ Semua paket berhasil diproses. Mempersiapkan pembelian paket utama..."

                                     
    if not status_message_id:
        msg = await context.bot.send_message(user_id, current_status_text, parse_mode="Markdown")
        automatic_xcs_flow_state['overall_status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=current_status_text, parse_mode="Markdown")
        except Exception as e:
            if "message is not modified" not in str(e):
                logging.warning(f"Gagal mengedit pesan status XCS {status_message_id}: {e}.")

                                                                         
                                                                            
                                                                         
    if current_addon_index < len(addons_to_process):
        addon_code = addons_to_process[current_addon_index]
        addon_info = next((pkg for pkg in ADD_ON_SEQUENCE if pkg['code'] == addon_code), None)
        
        if not addon_info:
            logging.error(f"Paket ADD ON tidak dikenal ({addon_code}). Melewatkan.")
            addon_results[addon_code] = {"success": False, "error_message": "Paket tidak dikenal"}
            automatic_xcs_flow_state['current_addon_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return

        addon_name = addon_info['name']
        addon_price = CUSTOM_PACKAGE_PRICES.get(addon_code, {}).get('price_bot', 0)

        addon_purchase_result = await execute_single_purchase_30h(
            update, context, user_id, addon_code, addon_name, phone, access_token, "BALANCE", addon_price,
            "automatic_xcs_addon_flow",
            automatic_xcs_flow_state['addon_pending_retry_count'] + 1
        )
        addon_results[addon_code] = addon_purchase_result

                                                                           
        if addon_purchase_result.get('fatal_error'):
            logging.critical(f"FATAL ERROR (Token Expired) pada alur XCS otomatis untuk user {user_id}. Menghentikan semua proses dan merefund sisa saldo.")
            
                                                           
            total_price_to_refund = context.user_data.pop('total_automatic_xcs_price', 0)
            
                                                                                      
            already_refunded = addon_purchase_result.get('refunded_amount', 0)
            
                                             
            remaining_refund = total_price_to_refund - already_refunded

                                   
            if remaining_refund > 0:
                user_data["registered_users"][str(user_id)]["balance"] += remaining_refund
                simpan_data_ke_db()

                                              
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUARSA* ⚠️\n"
                "Semua proses pembelian otomatis telah dihentikan.\n\n"
                f"Total saldo sebesar *Rp{total_price_to_refund:,}* telah dikembalikan ke akun Anda.\n"
                "Silakan login ulang dan coba lagi."
            )
            
            status_message_id = automatic_xcs_flow_state.get('overall_status_message_id')
            if status_message_id:
                try:
                    await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=user_facing_error, parse_mode="Markdown")
                except Exception:
                    await context.bot.send_message(user_id, user_facing_error, parse_mode="Markdown")
            else:
                await context.bot.send_message(user_id, user_facing_error, parse_mode="Markdown")

                                             
            del context.user_data['automatic_xcs_flow_state']
            await send_main_menu(update, context)
            return
                                 

        if addon_purchase_result['success']:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"✅ Pembelian *{addon_name}* berhasil! Melanjutkan...", parse_mode="Markdown")
            automatic_xcs_flow_state['addon_pending_retry_count'] = 0
            automatic_xcs_flow_state['current_addon_index'] += 1
            await asyncio.sleep(10)
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))

        elif addon_purchase_result.get('specific_action') == 'countdown_retry':
            if automatic_xcs_flow_state['flow_has_waited']:
                logging.warning(f"User {user_id} - {phone}: ADD ON {addon_name} pending, tetapi bot sudah pernah menunggu. Dianggap GAGAL.")
                unique_failure_id = str(uuid.uuid4())
                failed_attempts_for_reprocess[unique_failure_id] = {
                    "package_code": addon_code, "package_name": addon_name, "price_bot": addon_price, "error_message": "Pending kedua kali, dianggap gagal."
                }
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"⚠️ Pembelian *{addon_name}* pending lagi. Ini dianggap kegagalan dan akan dicoba ulang nanti. Melanjutkan...", parse_mode="Markdown")
                automatic_xcs_flow_state['addon_pending_retry_count'] = 0
                automatic_xcs_flow_state['current_addon_index'] += 1
                await asyncio.sleep(10)
            else:
                automatic_xcs_flow_state['flow_has_waited'] = True
                logging.info(f"User {user_id} - {phone}: ADD ON {addon_name} pending. Memulai countdown 10 menit.")
                countdown_msg = await context.bot.send_message(user_id, f"⏳ Pembelian *{addon_name}* pending. Menunggu 10 menit sebelum mencoba lagi...", parse_mode="Markdown")
                await asyncio.sleep(600)
                await countdown_msg.delete()
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        else:
            automatic_xcs_flow_state['addon_pending_retry_count'] += 1
            if automatic_xcs_flow_state['addon_pending_retry_count'] >= MAX_ADDON_PURCHASE_RETRIES:
                logging.error(f"User {user_id} - {phone}: ADD ON {addon_name} gagal setelah {MAX_ADDON_PURCHASE_RETRIES} percobaan.")
                unique_failure_id = str(uuid.uuid4())
                failed_attempts_for_reprocess[unique_failure_id] = {
                    "package_code": addon_code, "package_name": addon_name, "price_bot": addon_price, "error_message": addon_purchase_result.get('error_message', 'Gagal')
                }
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian *{addon_name}* gagal total dan dicatat untuk dicoba ulang nanti. Melanjutkan...", parse_mode="Markdown")
                automatic_xcs_flow_state['addon_pending_retry_count'] = 0
                automatic_xcs_flow_state['current_addon_index'] += 1
                await asyncio.sleep(10)
            else:
                logging.info(f"User {user_id} - {phone}: ADD ON {addon_name} gagal. Mencoba lagi.")
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian *{addon_name}* gagal. Mencoba lagi...", parse_mode="Markdown")
                await asyncio.sleep(10)
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                   
                                                                         
    if current_addon_index >= len(addons_to_process) and failed_attempts_for_reprocess and not automatic_xcs_flow_state.get('reprocessing_countdown_initiated', False):
        automatic_xcs_flow_state['reprocessing_countdown_initiated'] = True
        
                                                                                      
        automatic_xcs_flow_state['reprocessing_queue'] = list(failed_attempts_for_reprocess.keys())
        
        logging.info(f"User {user_id} - {phone}: Fase 1 selesai, ditemukan {len(failed_attempts_for_reprocess)} kegagalan. Memulai jeda 4 menit.")
        await context.bot.edit_message_text(
            chat_id=user_id, message_id=status_message_id, 
            text="✅ Pemrosesan awal selesai. Ditemukan beberapa paket yang gagal. Akan dicoba lagi setelah jeda.",
            parse_mode="Markdown"
        )
        countdown_seconds = 240
        countdown_msg = await context.bot.send_message(user_id, f"⏳ Jeda 4 menit 0 detik sebelum mencoba ulang...", parse_mode="Markdown")
        for i in range(countdown_seconds, 0, -1):
            if i % 15 == 0 or i <= 10:
                minutes = i // 60
                seconds = i % 60
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id, message_id=countdown_msg.message_id,
                        text=f"⏳ Jeda sebelum mencoba ulang: *{minutes} menit {seconds} detik*"
                    )
                except Exception as e:
                    if "message is not modified" not in str(e): logging.warning(f"Gagal update countdown: {e}")
            await asyncio.sleep(1)
        try: await countdown_msg.delete()
        except Exception: pass
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                           
                                                                         
                                                                            
    if reprocessing_queue and current_reprocess_id_index < len(reprocessing_queue):
        unique_failure_id_to_retry = reprocessing_queue[current_reprocess_id_index]
        failure_details = failed_attempts_for_reprocess[unique_failure_id_to_retry]
        addon_code_to_retry = failure_details['package_code']
        addon_name_to_retry = failure_details['package_name']
        addon_price_to_retry = failure_details['price_bot']
        MAX_REPROCESS_ATTEMPTS = 3
        current_reprocess_attempt = reprocess_attempts_counter.setdefault(unique_failure_id_to_retry, 0)
        
        if current_reprocess_attempt >= MAX_REPROCESS_ATTEMPTS:
            logging.error(f"User {user_id} - {phone}: Percobaan ulang {addon_name_to_retry} gagal permanen setelah {MAX_REPROCESS_ATTEMPTS} kali.")
            automatic_xcs_flow_state['current_reprocess_id_index'] += 1
            asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
            return

        user_data["registered_users"][str(user_id)]["balance"] -= addon_price_to_retry
        simpan_data_ke_db()
        logging.info(f"User {user_id} saldo dipotong Rp{addon_price_to_retry} untuk percobaan ulang ADD ON {addon_name_to_retry}.")
        
        reprocess_result = await execute_single_purchase_30h(
            update, context, user_id, addon_code_to_retry, addon_name_to_retry, phone, access_token, "BALANCE", addon_price_to_retry,
            "automatic_xcs_addon_flow", current_reprocess_attempt + 1
        )
        reprocess_attempts_counter[unique_failure_id_to_retry] += 1

        if reprocess_result['success']:
            logging.info(f"User {user_id} - {phone}: Percobaan ulang ADD ON {addon_name_to_retry} berhasil.")
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"✅ Percobaan ulang *{addon_name_to_retry}* berhasil!", parse_mode="Markdown")
                                                                                                   
            del failed_attempts_for_reprocess[unique_failure_id_to_retry]
        else:
            logging.warning(f"User {user_id} - {phone}: Percobaan ulang ADD ON {addon_name_to_retry} masih gagal.")
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Percobaan ulang *{addon_name_to_retry}* masih gagal. Melanjutkan...", parse_mode="Markdown")

        automatic_xcs_flow_state['current_reprocess_id_index'] += 1
        await asyncio.sleep(10)
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                        
                                                                         
                                                                                                      
    if current_addon_index >= len(addons_to_process) and failed_attempts_for_reprocess and current_reprocess_id_index >= len(reprocessing_queue) and automatic_xcs_flow_state.get('reprocessing_pass_count', 1) < MAX_REPROCESSING_PASSES:
        automatic_xcs_flow_state['reprocessing_pass_count'] += 1
        automatic_xcs_flow_state['current_reprocess_id_index'] = 0                                  
        automatic_xcs_flow_state['reprocess_attempts_counter'] = {}                             
        
                                                                               
        automatic_xcs_flow_state['reprocessing_queue'] = list(failed_attempts_for_reprocess.keys())
        
        logging.info(f"User {user_id}: Memulai putaran proses ulang ke-{automatic_xcs_flow_state['reprocessing_pass_count']}.")
        
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"⚠️ Beberapa paket masih gagal. Menunggu 1 menit sebelum melakukan upaya terakhir...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(60)
        
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

                                                                         
                                                                                  
                                                                         
    if not automatic_xcs_flow_state['xcp_8gb_completed']:
        if failed_attempts_for_reprocess:
            final_error_text = f"❌ *Alur Otomatis Dihentikan* ❌\n\nBeberapa paket gagal permanen setelah {MAX_REPROCESSING_PASSES} putaran percobaan ulang. Pembelian *XCP 8GB* dibatalkan.\n\n*Paket yang Gagal Permanen:*\n"
            for fail_id, fail_details in failed_attempts_for_reprocess.items():
                final_error_text += f"- *{fail_details['package_name']}*: `{fail_details['error_message']}`\n"
            
            final_error_text += f"\nSaldo Anda saat ini: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*."
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=final_error_text, parse_mode="Markdown")
            
            del context.user_data['automatic_xcs_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        xcp_8gb_price_key = f"c03be70fb3523ac2ac440966d3a5920e_{payment_method_xcp_8gb}"
        if payment_method_xcp_8gb == "PULSA":
            xcp_8gb_price_key = "bdb392a7aa12b21851960b7e7d54af2c"
        
        xcp_8gb_code = "c03be70fb3523ac2ac440966d3a5920e"
        if payment_method_xcp_8gb == "PULSA":
            xcp_8gb_code = "bdb392a7aa12b21851960b7e7d54af2c"
            
        xcp_8gb_name = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('display_name', 'XCP 8GB')
        xcp_8gb_price = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
        
        await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"Mencoba membeli paket utama *{xcp_8gb_name}* untuk *{phone}*...", parse_mode="Markdown")
        
        xcp_8gb_purchase_result = await execute_automatic_xc_purchase(
            update, context, user_id, xcp_8gb_code, xcp_8gb_name, phone, access_token, payment_method_xcp_8gb, xcp_8gb_price
        )

        if xcp_8gb_purchase_result['success']:
            final_summary_text = (
                f"🎉 *Alur pembelian XCS ADD ON otomatis untuk *{phone}* telah selesai!*\n\n"
                f"Semua paket Add-On dan paket utama *{xcp_8gb_name}* berhasil dibeli."
            )
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=final_summary_text, parse_mode="Markdown")
            automatic_xcs_flow_state['xcp_8gb_completed'] = True
        else:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=f"❌ Pembelian paket utama *{xcp_8gb_name}* gagal: {xcp_8gb_purchase_result['error_message']}. Alur dihentikan.", parse_mode="Markdown")

        del context.user_data['automatic_xcs_flow_state']
        simpan_data_ke_db()
        await send_main_menu(update, context)

async def run_automatic_purchase_flow(update, context):
    user_id = update.effective_user.id
    user_data_entry = user_data["registered_users"].get(str(user_id), {})

    current_phone = context.user_data.get('automatic_purchase_phone')
    access_token = context.user_data.get('automatic_purchase_token')
    payment_method_for_xc = context.user_data.get('automatic_purchase_payment_method')

    if not current_phone or not access_token:
        await context.bot.send_message(user_id, "Sesi pembelian otomatis tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

    user_data_entry.setdefault('accounts', {}).setdefault(current_phone, {})
    automatic_flow_state = user_data_entry['accounts'][current_phone].setdefault('automatic_flow_state', {
        'xuts_completed': False,
        'xc_completed': False,
        'xuts_retry_count': 0,
        'current_step': 'xuts',
        'last_xuts_attempt_time': None,
        'status_message_id': None,
        'qris_countdown_message_id': None
    })

    status_message_id = automatic_flow_state['status_message_id']

    if not status_message_id:
        msg = await context.bot.send_message(user_id, f"Memulai alur pembelian otomatis untuk *{current_phone}*...", parse_mode="Markdown")
        automatic_flow_state['status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"Melanjutkan alur pembelian otomatis untuk *{current_phone}*...",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status awal untuk {current_phone}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, f"Melanjutkan alur pembelian otomatis untuk *{current_phone}*...", parse_mode="Markdown")
            automatic_flow_state['status_message_id'] = msg.message_id
            status_message_id = msg.message_id
    simpan_data_ke_db()

    if automatic_flow_state['current_step'] == 'xuts' and not automatic_flow_state['xuts_completed']:
        if automatic_flow_state['xuts_retry_count'] >= 5:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Gagal membeli XUTS untuk *{current_phone}* setelah {automatic_flow_state['xuts_retry_count']} percobaan. Melanjutkan ke pembelian XC 1+1GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS gagal setelah {automatic_flow_state['xuts_retry_count']} percobaan. Lanjut ke XC.")
            automatic_flow_state['xuts_completed'] = True
            automatic_flow_state['current_step'] = 'xc'
            simpan_data_ke_db()
            asyncio.create_task(run_automatic_purchase_flow(update, context))
            return

        xuts_price = CUSTOM_PACKAGE_PRICES.get(XUTS_PACKAGE_CODE, {}).get('price_bot', 0)
        if xuts_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket XUTS tidak ditemukan atau tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XUTS tidak valid ({xuts_price}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xuts_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket XUTS (harga bot: Rp{xuts_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XUTS. Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        automatic_flow_state['xuts_retry_count'] += 1
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli XUTS untuk *{current_phone}*... (Percobaan ke-{automatic_flow_state['xuts_retry_count']})",
            parse_mode="Markdown"
        )
        simpan_data_ke_db()

        xuts_purchase_result = await execute_automatic_xuts_purchase(
            update, context, user_id, XUTS_PACKAGE_CODE, current_phone, access_token, "PULSA", xuts_price, automatic_flow_state['xuts_retry_count']
        )

        if xuts_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian XUTS berhasil untuk *{current_phone}*! Melanjutkan ke pembelian XC 1+1GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS berhasil. Lanjut ke XC.")
            automatic_flow_state['xuts_completed'] = True
            automatic_flow_state['current_step'] = 'xc'
            simpan_data_ke_db()
            asyncio.create_task(run_automatic_purchase_flow(update, context))
        elif xuts_purchase_result.get('specific_action') == 'countdown_retry':
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"⚠️ XUTS pending untuk *{current_phone}*. Bot akan mencoba kembali dalam 10 menit. Mohon tunggu...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS pending (MyXL message). Memulai countdown 10 menit.")

            countdown_message_text = f"⏳ Menunggu 10 menit sebelum mencoba XUTS lagi untuk *{current_phone}* (percobaan ke-{automatic_flow_state['xuts_retry_count']}).\nSisa waktu: *10 menit*."
            countdown_msg = await context.bot.send_message(user_id, countdown_message_text, parse_mode="Markdown")
            automatic_flow_state['qris_countdown_message_id'] = countdown_msg.message_id
            simpan_data_ke_db()

            for i in range(9, -1, -1):
                await asyncio.sleep(60)
                if i > 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=automatic_flow_state['qris_countdown_message_id'],
                            text=f"⏳ Menunggu 10 menit sebelum mencoba XUTS lagi untuk *{current_phone}* (percobaan ke-{automatic_flow_state['xuts_retry_count']}).\nSisa waktu: *{i} menit*.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e) and "message to edit not found" not in str(e):
                            logging.warning(f"Gagal mengupdate countdown XUTS untuk user {user_id} - {current_phone}: {e}")
                        break
                else:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=automatic_flow_state['qris_countdown_message_id'],
                            text="✅ Waktu jeda XUTS selesai. Mencoba kembali...",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.warning(f"Gagal mengedit pesan countdown XUTS selesai untuk {current_phone}: {e}")

            if 'qris_countdown_message_id' in automatic_flow_state:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=automatic_flow_state['qris_countdown_message_id'])
                    del automatic_flow_state['qris_countdown_message_id']
                    simpan_data_ke_db()
                except Exception as e:
                    logging.warning(f"Gagal menghapus pesan countdown XUTS untuk user {user_id} - {current_phone}: {e}")

            asyncio.create_task(run_automatic_purchase_flow(update, context))
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian XUTS untuk *{current_phone}* gagal: {xuts_purchase_result['error_message']}. Mencoba lagi...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XUTS gagal. Mencoba lagi.")
            asyncio.create_task(run_automatic_purchase_flow(update, context))
        return

    if automatic_flow_state['current_step'] == 'xc' and not automatic_flow_state['xc_completed']:
                                                                                            
        xc_package_code = ""
        xc_price_key = ""
        xc_package_name_display = ""

        if payment_method_for_xc == "DANA":
            xc_package_code = XC1PLUS1GB_DANA_CODE
            xc_price_key = XC1PLUS1GB_DANA_CODE
            xc_package_name_display = CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB DANA')
        elif payment_method_for_xc == "BALANCE":
            xc_package_code = XC1PLUS1GB_PULSA_CODE
            xc_price_key = XC1PLUS1GB_PULSA_CODE
            xc_package_name_display = CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB PULSA')
        elif payment_method_for_xc == "QRIS":
            xc_package_code = XC1PLUS1GB_DANA_CODE                                   
            xc_price_key = XC1PLUS1GB_QRIS_CODE                                     
            xc_package_name_display = CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('display_name', 'XC 1+1GB QRIS')
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Metode pembayaran tidak valid untuk XC 1+1GB. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Metode pembayaran XC 1+1GB tidak valid ({payment_method_for_xc}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return
        
        xc_price = CUSTOM_PACKAGE_PRICES.get(xc_price_key, {}).get('price_bot', 0)
        
        if xc_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {xc_package_name_display} tidak ditemukan atau tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XC 1+1GB tidak valid ({xc_price}). Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xc_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {xc_package_name_display} (harga bot: Rp{xc_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XC 1+1GB. Menghentikan alur.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_data["registered_users"][str(user_id)]["balance"] -= xc_price
        simpan_data_ke_db()
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{xc_price:,}* untuk pembelian {xc_package_name_display}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{xc_price} untuk XC 1+1GB.")

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {xc_package_name_display} untuk *{current_phone}*...",
            parse_mode="Markdown"
        )
        simpan_data_ke_db()

        xc_purchase_result = await execute_automatic_xc_purchase(
            update, context, user_id, xc_package_code, xc_package_name_display, current_phone, access_token, payment_method_for_xc, xc_price                                  
        )

        if xc_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {xc_package_name_display} untuk *{current_phone}* berhasil! Alur otomatis selesai.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XC 1+1GB berhasil. Alur selesai.")
            automatic_flow_state['xc_completed'] = True
            automatic_flow_state['current_step'] = 'finished'
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {xc_package_name_display} untuk *{current_phone}* gagal: {xc_purchase_result['error_message']}. Alur otomatis dihentikan.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XC 1+1GB gagal. Alur dihentikan.")
            if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['automatic_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
        return

    if automatic_flow_state['current_step'] == 'finished':
        logging.info(f"User {user_id} - {current_phone}: Automatic flow completed (final cleanup).")
        if 'automatic_flow_state' in user_data_entry['accounts'][current_phone]:
            del user_data_entry['accounts'][current_phone]['automatic_flow_state']
        simpan_data_ke_db()
        await send_main_menu(update, context)
        return

async def run_automatic_xutp_flow(update, context):
    user_id = update.effective_user.id
    user_data_entry = user_data["registered_users"].get(str(user_id), {})

    current_phone = context.user_data.get('xutp_purchase_phone')
    access_token = context.user_data.get('xutp_purchase_token')
    payment_method_for_xcp_8gb = context.user_data.get('xutp_purchase_payment_method')

    if not current_phone or not access_token:
        await context.bot.send_message(user_id, "Sesi pembelian XUTP otomatis tidak valid atau kedaluwarsa. Silakan mulai ulang.")
        await send_main_menu(update, context)
        return

                                                               
    user_data_entry.setdefault('accounts', {}).setdefault(current_phone, {})
    xutp_flow_state = user_data_entry['accounts'][current_phone].setdefault('xutp_flow_state', {
        'initial_package_completed': False,                                   
        'xcp_8gb_completed': False,                
        'initial_package_retry_count': 0,
        'current_step': 'initial_package',                                           
        'last_initial_package_attempt_time': None,                           
        'status_message_id': None,                        
        'qris_countdown_message_id': None                  
    })

    status_message_id = xutp_flow_state['status_message_id']

                                              
    if not status_message_id:
        msg = await context.bot.send_message(user_id, f"Memulai alur pembelian XUTP otomatis untuk *{current_phone}*...", parse_mode="Markdown")
        xutp_flow_state['status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"Melanjutkan alur pembelian XUTP otomatis untuk *{current_phone}*...",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status awal XUTP untuk {current_phone}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, f"Melanjutkan alur pembelian XUTP otomatis untuk *{current_phone}*...", parse_mode="Markdown")
            xutp_flow_state['status_message_id'] = msg.message_id
            status_message_id = msg.message_id
    simpan_data_ke_db()

                                                                      
    if xutp_flow_state['current_step'] == 'initial_package' and not xutp_flow_state['initial_package_completed']:
        initial_package_code = XUTP_INITIAL_PACKAGE_CODE
        initial_package_name_display = CUSTOM_PACKAGE_PRICES.get(initial_package_code, {}).get('display_name', 'ADD ON PREMIUM')
        initial_package_price = CUSTOM_PACKAGE_PRICES.get(initial_package_code, {}).get('price_bot', 0)

        if xutp_flow_state['initial_package_retry_count'] >= 5:                                   
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Gagal membeli {initial_package_name_display} untuk *{current_phone}* setelah {xutp_flow_state['initial_package_retry_count']} percobaan. Melanjutkan ke pembelian XCP 8GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} gagal setelah {xutp_flow_state['initial_package_retry_count']} percobaan. Lanjut ke XCP 8GB.")
            xutp_flow_state['initial_package_completed'] = True
            xutp_flow_state['current_step'] = 'xcp_8gb'
            simpan_data_ke_db()
            asyncio.create_task(run_automatic_xutp_flow(update, context))
            return

        if initial_package_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {initial_package_name_display} tidak ditemukan atau tidak valid. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga {initial_package_name_display} tidak valid ({initial_package_price}). Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < initial_package_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {initial_package_name_display} (harga bot: Rp{initial_package_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk {initial_package_name_display}. Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_data["registered_users"][str(user_id)]["balance"] -= initial_package_price
        simpan_data_ke_db()
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{initial_package_price:,}* untuk percobaan pembelian {initial_package_name_display}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{initial_package_price} untuk {initial_package_name_display}.")

        xutp_flow_state['initial_package_retry_count'] += 1
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {initial_package_name_display} untuk *{current_phone}*... (Percobaan ke-{xutp_flow_state['initial_package_retry_count']})",
            parse_mode="Markdown"
        )
        simpan_data_ke_db()

                                                                                            
        initial_purchase_result = await execute_single_purchase_30h(
            update, context, user_id, initial_package_code, initial_package_name_display, current_phone, access_token, "BALANCE", initial_package_price, "xutp_method_selection_menu", xutp_flow_state['initial_package_retry_count']
        )

        if initial_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {initial_package_name_display} berhasil untuk *{current_phone}*! Melanjutkan ke pembelian XCP 8GB.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} berhasil. Lanjut ke XCP 8GB.")
            xutp_flow_state['initial_package_completed'] = True
            xutp_flow_state['current_step'] = 'xcp_8gb'
            simpan_data_ke_db()
            asyncio.create_task(run_automatic_xutp_flow(update, context))
        elif initial_purchase_result.get('specific_action') == 'countdown_retry':
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"⚠️ {initial_package_name_display} pending untuk *{current_phone}*. Bot akan mencoba kembali dalam 10 menit. Mohon tunggu...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} pending (MyXL message). Memulai countdown 10 menit.")

            countdown_message_text = f"⏳ Menunggu 10 menit sebelum mencoba {initial_package_name_display} lagi untuk *{current_phone}* (percobaan ke-{xutp_flow_state['initial_package_retry_count']}).\nSisa waktu: *10 menit*."
            countdown_msg = await context.bot.send_message(user_id, countdown_message_text, parse_mode="Markdown")
            xutp_flow_state['qris_countdown_message_id'] = countdown_msg.message_id
            simpan_data_ke_db()

            for i in range(9, -1, -1):
                await asyncio.sleep(60)
                if i > 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=xutp_flow_state['qris_countdown_message_id'],
                            text=f"⏳ Menunggu 10 menit sebelum mencoba {initial_package_name_display} lagi untuk *{current_phone}* (percobaan ke-{xutp_flow_state['initial_package_retry_count']}).\nSisa waktu: *{i} menit*.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e) and "message to edit not found" not in str(e):
                            logging.warning(f"Gagal mengupdate countdown XUTP initial package untuk user {user_id} - {current_phone}: {e}")
                        break
                else:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=user_id,
                            message_id=xutp_flow_state['qris_countdown_message_id'],
                            text="✅ Waktu jeda XUTP initial package selesai. Mencoba kembali...",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.warning(f"Gagal mengedit pesan countdown XUTP initial package selesai untuk {current_phone}: {e}")

            if 'qris_countdown_message_id' in xutp_flow_state:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=xutp_flow_state['qris_countdown_message_id'])
                    del xutp_flow_state['qris_countdown_message_id']
                    simpan_data_ke_db()
                except Exception as e:
                    logging.warning(f"Gagal menghapus pesan countdown XUTP initial package untuk user {user_id} - {current_phone}: {e}")

            asyncio.create_task(run_automatic_xutp_flow(update, context))
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {initial_package_name_display} untuk *{current_phone}* gagal: {initial_purchase_result['error_message']}. Mencoba lagi...",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: {initial_package_name_display} gagal. Mencoba lagi.")
            asyncio.create_task(run_automatic_xutp_flow(update, context))
        return

                                      
    if xutp_flow_state['current_step'] == 'xcp_8gb' and not xutp_flow_state['xcp_8gb_completed']:
        xcp_8gb_package_code = None
        xcp_8gb_price_key = None
        
        if payment_method_for_xcp_8gb == "DANA":
            xcp_8gb_package_code = XCP_8GB_DANA_CODE_FOR_XUTP
            xcp_8gb_price_key = XCP_8GB_DANA_CODE_FOR_XUTP
        elif payment_method_for_xcp_8gb == "PULSA":
            xcp_8gb_package_code = XCP_8GB_PULSA_CODE_FOR_XUTP
            xcp_8gb_price_key = XCP_8GB_PULSA_CODE_FOR_XUTP
        elif payment_method_for_xcp_8gb == "QRIS":
            xcp_8gb_package_code = XCP_8GB_DANA_CODE_FOR_XUTP                                             
            xcp_8gb_price_key = XCP_8GB_QRIS_CODE_FOR_XUTP                                 
        
        xcp_8gb_name = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('display_name', 'XCP 8GB')

        if xcp_8gb_price_key is None or xcp_8gb_package_code is None:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Konfigurasi paket XCP 8GB untuk XUTP tidak valid. Menghentikan alur otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Konfigurasi XCP 8GB untuk XUTP tidak valid.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        xcp_8gb_price = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
        
        if xcp_8gb_price <= 0:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Harga paket {xcp_8gb_name} tidak ditemukan atau tidak valid. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.error(f"User {user_id} - {current_phone}: Harga XCP 8GB tidak valid ({xcp_8gb_price}). Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return

        user_current_balance = user_data_entry.get("balance", 0)
        if user_current_balance < xcp_8gb_price:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Saldo Anda tidak cukup untuk membeli paket {xcp_8gb_name} (harga bot: Rp{xcp_8gb_price:,}). Saldo Anda saat ini: Rp{user_current_balance:,}. Menghentikan alur XUTP otomatis untuk *{current_phone}*.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: Saldo tidak cukup untuk XCP 8GB. Menghentikan alur.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
            return
        
        user_data["registered_users"][str(user_id)]["balance"] -= xcp_8gb_price
        simpan_data_ke_db()
        await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{xcp_8gb_price:,}* untuk pembelian {xcp_8gb_name}. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"User {user_id} - {current_phone}: saldo dipotong Rp{xcp_8gb_price} untuk XCP 8GB.")

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message_id,
            text=f"Mencoba membeli {xcp_8gb_name} untuk *{current_phone}*...",
            parse_mode="Markdown"
        )
        simpan_data_ke_db()

        xcp_8gb_purchase_result = await execute_automatic_xc_purchase(
            update, context, user_id, xcp_8gb_package_code, xcp_8gb_name, current_phone, access_token, payment_method_for_xcp_8gb, xcp_8gb_price
        )

        if xcp_8gb_purchase_result['success']:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"✅ Pembelian {xcp_8gb_name} untuk *{current_phone}* berhasil! Alur XUTP otomatis selesai.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XCP 8GB berhasil. Alur XUTP selesai.")
            xutp_flow_state['xcp_8gb_completed'] = True
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
        else:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"❌ Pembelian {xcp_8gb_name} untuk *{current_phone}* gagal: {xcp_8gb_purchase_result['error_message']}. Alur XUTP otomatis dihentikan.",
                parse_mode="Markdown"
            )
            logging.info(f"User {user_id} - {current_phone}: XCP 8GB gagal. Alur XUTP dihentikan.")
            if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
                del user_data_entry['accounts'][current_phone]['xutp_flow_state']
            simpan_data_ke_db()
            await send_main_menu(update, context)
        return

                                                     
    if xutp_flow_state['current_step'] == 'finished':
        logging.info(f"User {user_id} - {current_phone}: XUTP Automatic flow completed (final cleanup).")
        if 'xutp_flow_state' in user_data_entry['accounts'][current_phone]:
            del user_data_entry['accounts'][current_phone]['xutp_flow_state']
        simpan_data_ke_db()
        await send_main_menu(update, context)
        return

async def execute_automatic_xuts_purchase(update, context, user_id, package_code, phone, access_token, payment_method, deducted_balance, attempt):
    url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={package_code}&phone={phone}&access_token={access_token}&payment_method={payment_method}&price_or_fee=0"

    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    raw_api_response_content = None

                                                                       
    user_data_entry = user_data["registered_users"].get(str(user_id), {})
    user_current_balance = user_data_entry.get("balance", 0)

    if user_current_balance < deducted_balance:
                                                                                                
                                
        logging.error(f"User {user_id}: Saldo tidak cukup di execute_automatic_xuts_purchase. Saldo: {user_current_balance}, Dibutuhkan: {deducted_balance}")
        await context.bot.send_message(user_id, "❌ Saldo Anda tidak cukup untuk melanjutkan pembelian ini.")
        return {"success": False, "package_name": "XUTS", "error_message": "Saldo tidak cukup.", "refunded_amount": 0, "status_message": "Gagal"}

    user_data["registered_users"][str(user_id)]["balance"] -= deducted_balance
    simpan_data_ke_db()
    await context.bot.send_message(user_id, f"Saldo Anda terpotong: *Rp{deducted_balance:,}* untuk percobaan pembelian XUTS. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
    logging.info(f"User {user_id} saldo dipotong Rp{deducted_balance} untuk XUTS. Percobaan {attempt}.")
                                    

    try:
        def blocking_api_call():
            return requests.get(url, timeout=58)

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(None, blocking_api_call),
            timeout=60.0
        )

        raw_api_response_content = response.text

        result = {}
        api_message = ""
        api_status = False

        try:
            parsed_json = response.json()
            if isinstance(parsed_json, list):
                result = parsed_json[0] if parsed_json else {}
            else:
                result = parsed_json

            api_message = result.get('message', '').strip().replace('\r', '').replace('\n', '')
            api_status = result.get('status', False)
        except json.JSONDecodeError:
            logging.warning(f"Failed to decode JSON from XUTS API response: {raw_api_response_content[:200]}...")
            api_message = f"Invalid JSON response or non-JSON content: {raw_api_response_content[:100]}...".strip().replace('\r', '').replace('\n', '')
            api_status = False

        EXPECTED_SUCCESS_MESSAGE_CONTAINING_422 = "Error Message: 422 -> Failed call ipaas purchase, with status code:422 : null,".strip().replace('\r', '').replace('\n', '')
        EXPECTED_SUCCESS_MESSAGE_MYXL = "Paket berhasil dibeli. Silakan cek kuotanya via aplikasi MyXL (disarankan) dan/atau via SMS kamu".strip().replace('\r', '').replace('\n', '')

        if response.status_code == 200 and EXPECTED_SUCCESS_MESSAGE_CONTAINING_422 in api_message:
            logging.info(f"Pembelian XUTS (KMSP) untuk {phone} dianggap SUKSES (respon 200 dgn pesan 422). (Percobaan {attempt})")
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Paket (LOGIN - XUTS Sukses)", "package_code": package_code, "package_name": "XUTS", "phone": phone,
                "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil (Skenario 1)",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()

            user_info = user_data["registered_users"][str(user_id)]
            admin_message = (
                f"✅ *PEMBELIAN XUTS BERHASIL (LOGIN - Skenario 1)!* ✅\n"
                f"User ID: `{user_id}` (`{escape_markdown(user_info.get('first_name', 'N/A'), version=2)}` / `@{escape_markdown(user_info.get('username', 'N/A'), version=2)}`)\n"
                f"Nomor HP: `{phone}`\n"
                f"Kode Paket: `{package_code}` (XUTS)\n"
                f"Metode Pembayaran: `{payment_method}`\n"
                f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
                f"Sisa Saldo: `Rp{user_info.get('balance', 0):,}`\n"
                f"Waktu Transaksi: `{transaction_time_str}`"
            )
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
            return {"success": True, "package_name": "XUTS", "error_message": None, "refunded_amount": 0, "status_message": "Berhasil"}

        elif response.status_code == 200 and EXPECTED_SUCCESS_MESSAGE_MYXL in api_message:
            logging.info(f"Pembelian XUTS (KMSP) untuk {phone} dianggap SUKSES (respon 200 dgn pesan MyXL), perlu jeda & retry. (Percobaan {attempt})")

                                                                  
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Paket (LOGIN - XUTS Pending Retry) (Refund)", "package_code": package_code, "package_name": "XUTS", "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Pending (Refund)",                            
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            logging.info(f"Saldo user {user_id} dikembalikan Rp{deducted_balance} karena XUTS pending (MyXL message).")

            user_info = user_data["registered_users"][str(user_id)]
            admin_message = (
                f"⚠️ *PEMBELIAN XUTS PENDING (LOGIN - Skenario 2)!* ⚠️\n"
                f"User ID: `{user_id}` (`{escape_markdown(user_info.get('first_name', 'N/A'), version=2)}` / `@{escape_markdown(user_info.get('username', 'N/A'), version=2)}`)\n"
                f"Nomor HP: `{phone}`\n"
                f"Kode Paket: `{package_code}` (XUTS)\n"
                f"Metode Pembayaran: `{payment_method}`\n"
                f"Saldo Dipotong Awal: `Rp{deducted_balance:,}` (SUDAH DIREFUND)\n"
                f"Sisa Saldo: `Rp{user_info.get('balance', 0):,}`\n"
                f"Waktu Transaksi: `{transaction_time_str}`\n"
                f"Pesan API: `{escape_markdown(api_message, version=2)}`"
            )
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

                                                                                                            
            return {"success": False, "package_name": "XUTS", "error_message": "STATUS PENDING akan mencoba MEMBELI ulang dalam 10 menit.", "refunded_amount": deducted_balance, "status_message": "Pending (Retry)", "specific_action": "countdown_retry"}

        else:
            response.raise_for_status()
            raise ValueError(api_message or f'API LOGIN mengembalikan status false untuk {package_code} (tidak dikenal sebagai sukses XUTS).')

    except Exception as e:
                                                                                    
        error_type = type(e).__name__
        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)

        if isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Waktu tunggu habis. Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
            admin_facing_error = "Request timed out after 60 seconds (KMSP API - XUTS)"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Gagal terhubung. Tidak dapat terhubung ke server (Connection Timeout)."
            admin_facing_error = "Connection timed out (KMSP API - XUTS)"
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                if e.response and e.response.content:
                    response_json_content = {}
                    try:
                        response_json_content = e.response.json()
                    except json.JSONDecodeError:
                        pass

                    user_facing_error = f"Pesan dari server: {response_json_content.get('message', 'Terjadi kesalahan HTTP.')}"
                    admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - XUTS): {response_json_content.get('message', 'No message')}. Raw: {e.response.text}"
                else:
                    user_facing_error = "Menerima respons HTTP yang tidak valid dari server."
                    admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - XUTS) with no/invalid response content."
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respons yang tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - XUTS) with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)

        logging.error(f"Pembelian XUTS (KMSP) gagal untuk user {user_id}, percobaan {attempt}. Error: {str(e)}")
        logging.error(traceback.format_exc())

                                                                                          
        user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": "Pembelian Gagal (LOGIN - XUTS) (Refund)", "package_code": package_code, "package_name": "XUTS", "phone": phone,
            "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal (Refund)",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()
        logging.info(f"Saldo user {user_id} dikembalikan {deducted_balance} karena kegagalan pembelian XUTS (percobaan {attempt}).")

        admin_message = (f"❌ *PEMBELIAN XUTS GAGAL (LOGIN)!* ❌\n"
                         f"User ID: `{user_id}`\nNomor HP: `{phone}`\nKode Paket: `{package_code}` (XUTS)\n"
                         f"Error: `{error_type}` - `{admin_facing_error}` (Saldo direfund)\n"
                         f"Total Percobaan: `{attempt}`")
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

        return {"success": False, "package_name": "XUTS", "error_message": user_facing_error, "refunded_amount": deducted_balance, "status_message": "Gagal"}

async def execute_automatic_xc_purchase(update, context, user_id, package_code, package_name_display, phone, access_token, payment_method, deducted_balance):
    api_price_or_fee = 2500

    if payment_method == "DANA" or payment_method == "QRIS":
        api_price_or_fee = 2500
    elif payment_method == "BALANCE":
        api_price_or_fee = 2500

    actual_package_code_for_api = package_code
    
    url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={actual_package_code_for_api}&phone={phone}&access_token={access_token}&payment_method={payment_method}&price_or_fee={api_price_or_fee}"

    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    status_message_id = context.user_data.get('automatic_flow_state', {}).get('status_message_id') or \
                        context.user_data.get('automatic_xcs_flow_state', {}).get('overall_status_message_id')
    
    if not status_message_id:
        msg = await context.bot.send_message(user_id, f"Memproses pembelian *{package_name_display}* dari LOGIN...", parse_mode="Markdown")
        if 'automatic_flow_state' in context.user_data:
            context.user_data['automatic_flow_state']['status_message_id'] = msg.message_id
        elif 'automatic_xcs_flow_state' in context.user_data:
            context.user_data['automatic_xcs_flow_state']['overall_status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    else:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=f"Memproses pembelian *{package_name_display}* dari LOGIN...\nProses ini dapat memakan waktu hingga 60 detik. Harap tunggu.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status untuk XC purchase: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, f"Memproses pembelian *{package_name_display}* dari LOGIN...", parse_mode="Markdown")
            if 'automatic_flow_state' in context.user_data:
                context.user_data['automatic_flow_state']['status_message_id'] = msg.message_id
            elif 'automatic_xcs_flow_state' in context.user_data:
                context.user_data['automatic_xcs_flow_state']['overall_status_message_id'] = msg.message_id
            status_message_id = msg.message_id

    loop = asyncio.get_running_loop()

    try:
        def blocking_api_call():
            return requests.get(url, timeout=58)

        response = await asyncio.wait_for(
            loop.run_in_executor(None, blocking_api_call),
            timeout=60.0
        )

        try:
            await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
        except Exception:
            logging.warning(f"Gagal menghapus pesan status setelah panggilan API XC: {e}")

        response.raise_for_status()
        result = response.json()

        if isinstance(result, list): result = result[0] if result else {}

        api_message = result.get('message', '')
        api_status = result.get('status', False)

        if not api_status:
            raise ValueError(api_message or f'API LOGIN mengembalikan status false untuk {package_code}')

        data = result.get("data", {})

        is_qris = data.get("is_qris", False)
        qris_image_url = None

        user_message_to_send = ""
        user_keyboard = []

                                     
        if payment_method == "QRIS" and is_qris:
            qris_data = data.get("qris_data", {})
            qris_code_raw_string = qris_data.get("qr_code")
            remaining_time = qris_data.get("remaining_time")

            if not qris_code_raw_string or not remaining_time:
                raise ValueError("Data QRIS dari API tidak lengkap.")

            qris_image_url = f"https://quickchart.io/qr?text={qris_code_raw_string}&size=300"
            escaped_package_name_display = escape_markdown(package_name_display, version=2)

            pesan_info_qris = (
                f"Silakan scan QRIS untuk membayar *{escaped_package_name_display}*.\n\n"
                f"Setelah berhasil membayar, tekan tombol *'✅ Sudah Bayar'* di bawah.\n\n"
                f"⚠️ QRIS ini akan kedaluwarsa dalam *{remaining_time} detik*."
            )
            keyboard = [[InlineKeyboardButton("✅ Sudah Bayar", callback_data="qris_paid_manual_confirm")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            qris_photo_msg = await context.bot.send_photo(chat_id=user_id, photo=qris_image_url)
            qris_text_msg = await context.bot.send_message(user_id, pesan_info_qris, parse_mode="Markdown", reply_markup=reply_markup)

            context.user_data['active_qris_messages'] = {
                'photo': qris_photo_msg.message_id,
                'text': qris_text_msg.message_id
            }

            context.job_queue.run_once(
                qris_expiration_job,
                remaining_time,
                data={'user_id': user_id, 'qris_message_id': qris_text_msg.message_id, 'qris_photo_id': qris_photo_msg.message_id},
                name=f"qris_expiration_auto_{user_id}_{qris_text_msg.message_id}"
            )
                                      

        else:
            deeplink_url = data.get("deeplink_data", {}).get("deeplink_url")
            have_deeplink = data.get("have_deeplink", False)

            escaped_package_name_display = escape_markdown(package_name_display, version=2)
            user_message_to_send = f"🎉 *Pembelian {escaped_package_name_display} dari LOGIN Berhasil Diproses!*"

            if payment_method == "BALANCE":
                user_message_to_send += "\nPaket telah berhasil diaktifkan di nomormu. Silakan cek kuota."
            elif have_deeplink and deeplink_url:
                user_message_to_send += "\nSilakan lanjutkan pembayaran melalui link di bawah ini."
                user_keyboard.append([InlineKeyboardButton("💰 BAYAR SEKARANG", url=deeplink_url)])
            else:
                user_message_to_send += "\nPaket telah berhasil diaktifkan di nomormu. Silakan cek kuota."

            user_keyboard.append([InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")])
            await context.bot.send_message(user_id, user_message_to_send, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(user_keyboard))

        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": f"Pembelian Paket Otomatis (LOGIN - {payment_method})", "package_code": package_code, "package_name": package_name_display, "phone": phone,
            "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()

        user_info = user_data["registered_users"][str(user_id)]
        user_first_name = user_info.get("first_name", "N/A")
        user_username = user_info.get("username", "N/A")
        remaining_balance = user_info.get("balance", 0)

        escaped_package_name_display_admin = escape_markdown(package_name_display, version=2)
        admin_message = (
            f"✅ *PEMBELIAN OTOMATIS BERHASIL (LOGIN)!* ✅\n"
            f"User ID: `{user_id}`\n"
            f" (`{escape_markdown(user_first_name, version=2)}` / `@{escape_markdown(user_username, version=2)}`)\n"
            f"Nomor HP: `{phone}`\n"
            f"Kode Paket: `{package_code}`\n"
            f" ({escaped_package_name_display_admin})\n"
            f"Metode Pembayaran: `{payment_method}`\n"
            f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
            f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
            f"Waktu Transaksi: `{transaction_time_str}`"
        )
        if is_qris and qris_image_url:
            admin_message += f"\nQRIS Image URL: {qris_image_url}"

        admin_keyboard = None
        if not is_qris and data.get("have_deeplink", False) and data.get("deeplink_data", {}).get("deeplink_url"):
            admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Link Pembayaran User", url=data.get("deeplink_data", {}).get("deeplink_url"))]])

        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown", reply_markup=admin_keyboard)

        return {"success": True, "package_name": package_name_display, "error_message": None, "refunded_amount": 0}

    except Exception as e:
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
        except Exception:
            pass

        error_type = type(e).__name__
        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)

        if isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
            admin_facing_error = "Request timed out after 60 seconds"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Tidak dapat terhubung ke server (Connection Timeout)."
            admin_facing_error = "Connection timed out"
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "Terjadi kesalahan HTTP.")
                user_facing_error = f"Pesan dari API: {error_msg_from_api}"
                admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respons yang tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)

        escaped_package_name_display = escape_markdown(package_name_display, version=2)
        escaped_user_facing_error = escape_markdown(user_facing_error, version=2)
        escaped_admin_facing_error = escape_markdown(admin_facing_error, version=2)

        final_user_error_message = f"❌ Gagal melakukan pembelian *{escaped_package_name_display}* dari LOGIN.\n*Pesan Error:*\n`{escaped_user_facing_error}`"

        if deducted_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Otomatis Gagal (LOGIN) (Refund)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            final_user_error_message += f"\n💰 Saldo Anda sebesar *Rp{deducted_balance:,}* telah dikembalikan."

        await context.bot.send_message(user_id, final_user_error_message, parse_mode="Markdown")

        user_info = user_data["registered_users"][str(user_id)]
        user_first_name = user_info.get("first_name", "N/A")

        admin_message = (f"❌ *PEMBELIAN OTOMATIS GAGAL (LOGIN)!* ❌\nUser ID: `{user_id}` (`{user_first_name}`)\nNomor: `{phone}`\nPaket: `{package_name_display}`\n"
                         f"Error: `{admin_facing_error}` (Saldo direfund)")
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

        return {"success": False, "package_name": package_name_display, "error_message": user_facing_error, "refunded_amount": deducted_balance}

async def delete_last_message(user_id, context):
    messages = bot_messages.get(user_id, [])
    if messages:
        for msg_id in messages:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                if "message to delete not found" not in str(e):
                    logging.warning(f"Gagal hapus pesan {msg_id} untuk user {user_id}: {e}")
        bot_messages[user_id] = []

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_first_name = update.effective_user.first_name
    
    user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)
    total_users = len(user_data.get("registered_users", {}))
    
    uptime_delta = datetime.now() - bot_start_time
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d:{hours}j:{minutes}m"

    stats_block = (
        "💜 D O R  X L  H O K A G E  L E G E N D  S T O R E 💜\n"
        "╔══════════════════════════════╗\n"
        f"║ 🪪 *Nama* : {user_first_name}\n"
        f"║ 🆔 *ID User* : `{user_id}`\n"
        f"║ 💰 *Saldo Anda* : `Rp{user_balance:,}`\n"
        "╠══════════════════════════════╣\n"
        "║ 📊 *S T A T I S T I K  B O T*\n"
        "╠══════════════════════════════╣\n"
        f"║ 👥 *Total Pengguna* : {total_users} user\n"
        f"║ ⏱️ *Uptime Bot* : {uptime_str}\n"
        "╚══════════════════════════════╝\n\n"
        "🌸 *~ Selamat Berbelanja Di Hokage Legend ~* 🌸\n"
    )

    original_welcome_block = (
    "💜 *💠 D O R  X L  H O K A G E  P R I C E  L I S T 💠* 💜\n"
    "╔══════════════════════════════╗\n"
    "║ 🟣 *PAKET BUNDLING SPECIAL* 🟣\n"
    "╠══════════════════════════════╣\n"
    "║ • XUTS: Rp5.200\n"
    "║ • XCS ADDS-ON: Rp7.600 (full add on)\n"
    "║ • XUTP: Rp5.200\n"
    "╠══════════════════════════════╣\n"
    "║ 💜 *HARGA SATUAN* 💜\n"
    "╠══════════════════════════════╣\n"
    "║ • ADD ON: Rp200/add on\n"
    "║ • XC 1+1GB: Rp5000\n"
    "║ • XCP 8GB: Rp5000\n"
    "╠══════════════════════════════╣\n"
    "║ 🟣 *PAKET LAINNYA* 🟣\n"
    "╠══════════════════════════════╣\n"
    "║ • XL VIDIO: Rp5000\n"
    "║ • XL IFLIX: Rp5000\n"
    "║ • *CEK MENU PAKET LAINNYA*\n"
    "╚══════════════════════════════╝\n\n"
    "🟣 *⚠️  P E N T I N G  D I B A C A  ⚠️* 🟣\n"
    "╔══════════════════════════════╗\n"
    "║ ⛔ *Paket Unofficial (Tanpa Garansi)*\n"
    "╠══════════════════════════════╣\n"
    "║ ‼️ *WAJIB CEK TUTORIAL BELI*\n"
    "║ ‼️ *Cek Kuota terlebih dahulu!*\n"
    "║ ‼️ *Hindari semua jenis kuota XTRA COMBO*\n"
    "║ ❌ *Unreg paket ini jika ada* ❌\n"
    "╠══════════════════════════════╣\n"
    "║ - XTRA COMBO ❌\n"
    "║ - XTRA COMBO VIP ❌\n"
    "║ - XTRA COMBO MINI ❌\n"
    "║ - XTRA COMBO VIP PLUS ❌\n"
    "╠══════════════════════════════╣\n"
    "║ 💜 *Pastikan semua langkah dilakukan dengan benar* 💜\n"
    "╚══════════════════════════════╝\n\n"
    "🌸 *~ Silakan pilih menu di bawah ini ~* 🌸"
)
    text = stats_block + original_welcome_block
    
    logging.info(f"Mengirim menu utama gabungan ke user {user_id}")

    keyboard = [
        [InlineKeyboardButton("🔮 LOGIN OTP", callback_data='show_login_options'),
         InlineKeyboardButton("🆔 NOMOR SAYA", callback_data="akun_saya")],
        [InlineKeyboardButton("⚡ Tembak Paket", callback_data='tembak_paket')],
        [InlineKeyboardButton("👾 XL VIDIO", callback_data='vidio_xl_menu'),
         InlineKeyboardButton("🍇 XL IFLIX", callback_data='iflix_xl_menu')],
        [InlineKeyboardButton("📶 Cek Kuota", callback_data='cek_kuota'),
         InlineKeyboardButton("💰 Cek Saldo", callback_data='cek_saldo')],
        [InlineKeyboardButton("📚 Tutorial Beli", callback_data='tutorial_beli'),
         InlineKeyboardButton("💸 Top Up Saldo", callback_data='top_up_saldo')],
        [InlineKeyboardButton("📦 Paket Lainnya", callback_data='show_custom_packages')],
        [InlineKeyboardButton("💜 Kontak Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan menu untuk user {user_id}: {e}. Mengirim pesan baru.")
            await context.bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def show_login_options_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "Silakan pilih jenis login OTP yang Anda inginkan:"
    keyboard = [
        [InlineKeyboardButton("🔐 LOGIN OTP", callback_data='login_kmsp')],                    
        [InlineKeyboardButton("🔑 LOGIN OTP BYPASS", callback_data='login_hesda')],                     
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan show_login_options_menu untuk user {user_id}: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
                                                                            
        msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id_str = str(user.id)
    user_first_name = user.first_name or "N/A"
    user_username = user.username or "N/A"
    
    logging.info(f"User {user_id_str} mengakses /start. Memvalidasi data pengguna...")

    is_new_user = user_id_str not in user_data["registered_users"]

    user_details = user_data["registered_users"].setdefault(user_id_str, {
        "accounts": {}, "balance": 0, "transactions": [], "selected_hesdapkg_ids": [],
        "selected_30h_pkg_ids": [] 
    })
    
    user_details['first_name'] = user_first_name
    user_details['username'] = user_username

    if is_new_user:
        logging.info(f"User baru terdaftar: ID={user_id_str}, Nama={user_first_name}, Username=@{user_username}")
        admin_notification_text = (
            f"🎉 *User Baru Terdaftar!* 🎉\n"
            f"ID User: `{user_id_str}`\n"
            f"Nama: `{user_first_name}`\n"
            f"Username: `@{user_username}`\n"
            f"Waktu: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        try:
            await context.bot.send_message(ADMIN_ID, admin_notification_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Gagal mengirim notifikasi user baru ke admin: {e}")

    simpan_data_ke_db()
    await delete_last_message(user_id_str, context)
    await send_main_menu(update, context)

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        return True

    if user_id in user_data.get("blocked_users", []):
        message_text = "ANDA TELAH DIBLOKIR DAN TIDAK DAPAT MENGAKSES BOT INI. Silakan hubungi admin."
        if update.callback_query:
            await update.callback_query.answer(message_text, show_alert=True)
            try:
                await update.callback_query.edit_message_text(message_text)
            except Exception as e:
                logging.warning(f"Gagal mengedit pesan untuk user {user_id} saat diblokir: {e}")
                await context.bot.send_message(user_id, message_text)
        elif update.message:
            await update.message.reply_text(message_text)
        logging.warning(f"Akses ditolak untuk user {user_id} (diblokir).")
        return False

    return True

async def get_kmsp_balance():
    try:
        url = f"https://golang-openapi-panelaccountbalance-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        api_response = response.json()
        logging.info(f"KMSP balance API response: {api_response}")

        if isinstance(api_response, dict) and 'data' in api_response and isinstance(api_response.get('data'), dict):
            balance_value = api_response['data'].get('balance')
            if balance_value is not None:
                try:
                    formatted_balance = f"Rp{int(float(balance_value)):,}"
                    return formatted_balance
                except (ValueError, TypeError):
                    logging.error(f"Gagal mengonversi nilai saldo '{balance_value}' menjadi angka.")
                    return "Format saldo tidak valid"

        message = api_response.get('message', 'Respons API tidak dikenali.')
        logging.warning(f"Struktur respons API KMSP tidak seperti yang diharapkan. Pesan: {message}")
        return f"Info dari API: {message}"

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error saat mengambil saldo KMSP: {e}")
        return "API tidak dapat diakses (HTTP Error)"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error jaringan saat mengambil saldo KMSP: {e}")
        return "Gagal terhubung ke server API"
    except json.JSONDecodeError:
        logging.error(f"Gagal memecah JSON dari API saldo KMSP. Respon: {response.text}")
        return "Respons API tidak valid (Bukan JSON)"
    except Exception as e:
        logging.error(f"Kesalahan tak terduga saat mengambil saldo KMSP: {e}", exc_info=True)
        return "Kesalahan tak terduga terjadi"

async def jalankan_cek_kuota_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    nomor_input = update.message.text.strip()

    if not re.match(r'^(08|62)\d{8,12}$', nomor_input):
        await update.message.reply_text(
            '❌ Format nomor tidak valid. Masukkan nomor dalam format `08xxxx` atau `62xxxx`.',
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'handle_cek_kuota_baru_input'
        return

    if nomor_input.startswith('08'):
        nomor = '62' + nomor_input[1:]
    else:
        nomor = nomor_input
        
    status_msg = await update.message.reply_text("🔍 Sedang mengecek kuota, harap tunggu...", parse_mode="Markdown")

    try:
        url = f"https://apigw.kmsp-store.com/sidompul/v4/cek_kuota?msisdn={nomor}&isJSON=true"
        headers = {
            "Authorization": "Basic c2lkb21wdWxhcGk6YXBpZ3drbXNw",
            "X-API-Key": "60ef29aa-a648-4668-90ae-20951ef90c55",
            "X-App-Version": "4.0.0"
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status() 
        
        response_json = response.json()
        
        await status_msg.delete()

        if response_json.get('status'):
            hasil_kotor = response_json.get("data", {}).get("hasil", "Tidak ada data.")
            hasil_bersih = html.unescape(hasil_kotor).replace('<br>', '\n').replace('MSISDN', 'NOMOR')
            
            final_text = f"✅ *Hasil Pengecekan Kuota untuk {nomor}*\n\n```{hasil_bersih}```"
            
            keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(user_id, final_text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            error_text = response_json.get("message", "Gagal mengambil data kuota.")
            await context.bot.send_message(user_id, f"❌ Terjadi kesalahan: `{error_text}`", parse_mode="Markdown")
            await send_main_menu(update, context)

    except requests.exceptions.ConnectionError as e:                                   
        logging.error(f"Connection Error Cek Kuota Baru untuk nomor {nomor}: {e}", exc_info=True)
        await status_msg.delete()
        await context.bot.send_message(user_id, "❌ Gagal terhubung ke server pengecekan kuota. Mohon coba lagi nanti.")
        await send_main_menu(update, context)
    except requests.exceptions.Timeout as e:                       
        logging.error(f"Timeout Error Cek Kuota Baru untuk nomor {nomor}: {e}", exc_info=True)
        await status_msg.delete()
        await context.bot.send_message(user_id, "❌ Waktu tunggu habis saat mengecek kuota. Mohon coba lagi nanti.")
        await send_main_menu(update, context)
    except requests.exceptions.RequestException as e:                                 
        logging.error(f"General Request Error Cek Kuota Baru untuk nomor {nomor}: {e}", exc_info=True)
        await status_msg.delete()
        await context.bot.send_message(user_id, "❌ Terjadi kesalahan saat request pengecekan kuota. Mohon coba lagi nanti.")
        await send_main_menu(update, context)
    except Exception as e:
        logging.error(f"Error tak terduga di jalankan_cek_kuota_baru: {e}", exc_info=True)
        await status_msg.delete()
        await context.bot.send_message(user_id, "❌ Terjadi kesalahan tak terduga. Silakan hubungi admin.")
        await send_main_menu(update, context)

async def get_api_package_details(package_code: str):
    try:
        url = f"https://golang-openapi-packagelist-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        all_packages = response.json().get("data", [])
        
        for package in all_packages:
            if package.get("package_code") == package_code:
                return package                                           
        return None                                       
    except requests.RequestException as e:
        logging.error(f"Gagal mengambil list paket dari API: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Gagal memecah JSON dari API list paket.")
        return None

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return

    msg_info = None
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text("Memuat data statistik, harap tunggu...")
            msg_info = update.callback_query.message
        except Exception:
             msg_info = await context.bot.send_message(user_id, "Memuat data statistik, harap tunggu...")
    else:
        msg_info = await context.bot.send_message(user_id, "Memuat data statistik, harap tunggu...")


    total_users = len(user_data.get("registered_users", {}))
    kmsp_balance = await get_kmsp_balance()

    header_text = (
        f"📊 *Statistik Bot*\n"
        f"👥 Total Pengguna: *{total_users}*\n"
        f"💰 Saldo Akun LOGIN: *{kmsp_balance}*\n\n"                        
        "👑 *Panel Admin Bot XL Tembak*\n"
        "Pilih tindakan yang ingin Anda lakukan:"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ Tambah Saldo", callback_data='admin_add_balance'),
            InlineKeyboardButton("➖ Kurangi Saldo", callback_data='admin_deduct_balance')
        ],
        [InlineKeyboardButton("💰 Cek Saldo User", callback_data='admin_check_user_balances')],
        [InlineKeyboardButton("👥 Daftar User", callback_data='admin_list_users')],

        [
            InlineKeyboardButton("🚫 Blokir", callback_data='admin_block_user_menu'),
            InlineKeyboardButton("✅ Un-Blokir", callback_data='admin_unblock_user_menu')
        ],
        [
            InlineKeyboardButton("🔍 Cari User", callback_data='admin_search_user_menu'),
            InlineKeyboardButton("🧾 Riwayat User", callback_data='admin_check_user_transactions_menu')
        ],
        [
            InlineKeyboardButton("📦 Kelola Paket API", callback_data='admin_check_api_packages'),
            InlineKeyboardButton("🔍 Cari Paket API", callback_data='admin_search_api_package_menu')
        ],
        [
            InlineKeyboardButton("➕ Paket Kustom", callback_data='admin_add_custom_package'),
            InlineKeyboardButton("✏️ Edit Paket Kustom", callback_data='admin_edit_custom_package_menu')
        ],
        [InlineKeyboardButton("📢 Broadcast Pesan", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🏠 Kembali ke Menu User", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=msg_info.message_id,
            text=header_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan admin menu: {e}. Mengirim pesan baru.")
        await context.bot.delete_message(chat_id=user_id, message_id=msg_info.message_id)
        await context.bot.send_message(user_id, header_text, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_check_user_balances(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    try:
        query = update.callback_query
        all_users = user_data.get("registered_users", {})

        user_balances = [
            {
                "id": uid,
                "name": details.get("first_name", "N/A"),
                "username": details.get("username", "N/A"),
                "balance": details.get("balance", 0)
            } for uid, details in all_users.items()
        ]

        sorted_users = sorted(user_balances, key=lambda x: x['balance'], reverse=True)
        
        start_index = page * USERS_PER_PAGE_ADMIN
        end_index = start_index + USERS_PER_PAGE_ADMIN
        paginated_users = sorted_users[start_index:end_index]

        if not paginated_users and page == 0:
            text = "Tidak ada user terdaftar untuk ditampilkan."
            keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        elif not paginated_users:
            await query.answer("Anda sudah di halaman terakhir.", show_alert=True)
            return

        response_text = f"💰 *Daftar Saldo User (Hal. {page + 1})*\n(Terbesar ke Terkecil)\n\n"
        for i, user in enumerate(paginated_users, start=start_index + 1):
            response_text += (
                f"*{i}.* Nama: `{user['name']}` (@`{user['username']}`)\n"
                f"   ID: `{user['id']}`\n"
                f"   Saldo: *Rp{user['balance']:,}*\n\n"
            )
        
        keyboard = []
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⏪ Sebelumnya", callback_data=f"admin_user_balance_page_{page-1}"))
        if end_index < len(sorted_users):
            nav_buttons.append(InlineKeyboardButton("Berikutnya ⏩", callback_data=f"admin_user_balance_page_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logging.error(f"Error di admin_check_user_balances: {e}", exc_info=True)
        error_text = (
            "❌ *Terjadi Error Saat Menampilkan Saldo User*\n"
            "Bot mengalami masalah saat mencoba memproses permintaan Anda.\n"
            f"*Detail Error:*\n`{type(e).__name__}: {e}`\n"
            "Silakan periksa file `botxl.log` untuk informasi lebih lanjut atau laporkan error ini."
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_text(error_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as edit_e:
            logging.error(f"Gagal mengedit pesan error, mengirim pesan baru: {edit_e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_display_user_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    user_id_admin = update.effective_user.id
    query = update.callback_query                                        
    
                                                                                           
    target_user_id_str = context.user_data.get('current_viewed_transactions_user_id')

    if not target_user_id_str or target_user_id_str not in user_data["registered_users"]:
        text = "❌ Data pengguna tidak ditemukan atau sesi kadaluarsa."
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await context.bot.send_message(user_id_admin, text, parse_mode="Markdown", reply_markup=reply_markup)
        return

    user_info = user_data["registered_users"][target_user_id_str]
    transactions = user_info.get('transactions', [])
    
                                                                            
    sorted_transactions = sorted(transactions, key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'), reverse=True)

    start_index = page * TRANSACTIONS_PER_PAGE_ADMIN
    end_index = start_index + TRANSACTIONS_PER_PAGE_ADMIN
    paginated_transactions = sorted_transactions[start_index:end_index]

    response_text_parts = []
    response_text_parts.append(f"*Riwayat Transaksi untuk User:*\n")
    response_text_parts.append(f"ID: `{target_user_id_str}`")
    response_text_parts.append(f"Nama: `{user_info.get('first_name', 'N/A')}`")
    response_text_parts.append(f"Username: `@{user_info.get('username', 'N/A')}`")
    response_text_parts.append(f"Saldo Saat Ini: `Rp{user_info.get('balance', 0):,}`\n")
    response_text_parts.append(f"--- Riwayat Transaksi (Hal. {page + 1}/{math.ceil(len(sorted_transactions) / TRANSACTIONS_PER_PAGE_ADMIN)}) ---\n")

    if paginated_transactions:
        for tx in paginated_transactions:
            response_text_parts.append(f"• Tipe: `{tx.get('type', 'N/A')}`")
            response_text_parts.append(f"  Nominal: `Rp{tx.get('amount', 0):,}`")
            response_text_parts.append(f"  Waktu: `{tx.get('timestamp', 'N/A')}`")
            if tx.get('package_code'):
                response_text_parts.append(f"  Paket: `{tx['package_code']}`")
            if tx.get('phone'):
                response_text_parts.append(f"  Nomor HP: `{tx['phone']}`")
            if tx.get('amount', 0) < 0:
                response_text_parts.append(f"  Saldo Dipotong: `Rp{-tx.get('amount', 0):,}`")
            else:
                response_text_parts.append(f"  Saldo Ditambahkan: `Rp{tx.get('amount', 0):,}`")
            if 'balance_after_tx' in tx:
                response_text_parts.append(f"  Sisa Saldo: `Rp{tx['balance_after_tx']:,}`")
            else:
                response_text_parts.append(f"  Sisa Saldo: `N/A (Data lama)`")
            response_text_parts.append(f"---------------------------\n")
    else:
        response_text_parts.append(" _Tidak ada riwayat transaksi ditemukan untuk user ini pada halaman ini._")
    
    keyboard = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏪ Sebelumnya", callback_data=f"admin_tx_page_{page-1}"))
    if end_index < len(sorted_transactions):
        nav_buttons.append(InlineKeyboardButton("Berikutnya ⏩", callback_data=f"admin_tx_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text_to_send = "\n".join(response_text_parts)

    try:
        if query:
            await query.edit_message_text(text_to_send, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await context.bot.send_message(user_id_admin, text_to_send, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error displaying user transactions for admin: {e}", exc_info=True)
        error_message = "Terjadi kesalahan saat menampilkan riwayat transaksi."
        if query:
            await query.answer(error_message, show_alert=True)
        else:
            await context.bot.send_message(user_id_admin, error_message)

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        await query.answer("Anda tidak memiliki izin untuk tindakan ini.", show_alert=True)
        return

                                                              
    if data.startswith('hesda_api_res_'):
        await query.answer("Mengambil respon API...")
                                      
        key_parts = data.split('_')
                                                                 
        if len(key_parts) < 4:                           
            await context.bot.send_message(user_id, "❌ Kunci respon API tidak valid atau sudah kedaluwarsa.")
            logging.warning(f"Invalid hesda_api_res_ callback data: {data}")
            return

        unique_key = key_parts[3]                                  
        full_context_key = f" Bethesda_API_Response_Data_{unique_key}"                                        
        raw_response_json_str = context.bot_data.get(full_context_key)

        if raw_response_json_str:
            try:
                pretty_json = json.dumps(json.loads(raw_response_json_str), indent=2, ensure_ascii=False)
                await context.bot.send_message(
                    user_id,
                    f"📄 *Respon API BYPAS:*\n```json\n{pretty_json}\n```",                         
                    parse_mode="Markdown"
                )
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON for admin view. Raw content: {raw_response_json_str[:500]}...")                      
                await context.bot.send_message(user_id, f"❌ Gagal mem-parsing JSON respon API. Respon mentah:\n`{raw_response_json_str[:100]}...`", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Error saat menampilkan respon API Hesda ke admin: {e}", exc_info=True)
                await context.bot.send_message(user_id, "Terjadi kesalahan saat menampilkan detail respon API.")
            finally:
                                                                                    
                if full_context_key in context.bot_data:
                    del context.bot_data[full_context_key]
                    logging.info(f"Deleted temporary API response data for key: {full_context_key}")
        else:
            await context.bot.send_message(user_id, "❌ Data respon API tidak ditemukan atau sudah kedaluwarsa.", parse_mode="Markdown")
        return

                                                        
    if data.startswith('retry_single_'):                                             
        await query.answer()                              
        key_parts = data.split('_')
        if len(key_parts) < 3:                               
            await context.bot.send_message(user_id, "❌ Kunci data retry tidak valid atau sudah kedaluwarsa.")
            logging.warning(f"Invalid retry_single_ callback data: {data}")
            return
        
        unique_key = key_parts[2]
        full_context_key = f"retry_data_{unique_key}"                                                 
        
        retry_payload_str = context.bot_data.get(full_context_key)

        if not retry_payload_str:
            await context.bot.send_message(user_id, "❌ Data untuk percobaan ulang tidak ditemukan atau sudah kedaluwarsa. Silakan coba beli dari awal.")
            return

        try:
            retry_payload = json.loads(retry_payload_str)
            
            provider = retry_payload.get('provider')
            package_id_or_code = retry_payload['package_id_or_code']
            package_name = retry_payload['package_name']
            phone = retry_payload['phone']
            payment_method = retry_payload['payment_method']
            deducted_balance = retry_payload['deducted_balance']
            return_menu_callback_data = retry_payload['return_menu_callback_data']

                                                                                            
            try:
                if query.message:
                    await query.message.delete()
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan error sebelum retry: {e}")

            user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
            if user_current_balance < deducted_balance:
                await context.bot.send_message(user_id, f"❌ Gagal mencoba lagi: Saldo tidak cukup (dibutuhkan Rp{deducted_balance:,}). Saldo Anda saat ini: Rp{user_current_balance:,}.")
                return

                                                                                
            if deducted_balance > 0:
                user_data["registered_users"][str(user_id)]["balance"] -= deducted_balance
                simpan_data_ke_db()
                await context.bot.send_message(user_id, f"Mencoba lagi pembelian... Saldo Anda terpotong: *Rp{deducted_balance:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")

            if provider == "kmsp":
                                                                                 
                current_phone_in_user_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("current_phone")
                access_token = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(current_phone_in_user_data, {}).get("kmsp", {}).get("access_token")
                if not access_token:
                    await context.bot.send_message(user_id, "Gagal mencoba lagi: Token LOGIN tidak ditemukan. Silakan login ulang LOGIN.")
                    return
                asyncio.create_task(execute_single_purchase(update, context, user_id, package_id_or_code, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, provider="kmsp"))
            
            elif provider == "hesda":
                                                                                                                            
                phone_for_hesda_retry = phone                                                  
                access_token_hesda = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone_for_hesda_retry, {}).get("hesda", {}).get("access_token")
                
                if not access_token_hesda:
                    await context.bot.send_message(user_id, f"Gagal mencoba lagi: Token BYPAS tidak ditemukan untuk nomor `{phone_for_hesda_retry}`. Silakan login ulang BYPAS untuk nomor ini.")
                                                                           
                    context.user_data['pending_hesda_package_details'] = {
                        'id': package_id_or_code, 
                        'name': package_name, 
                        'price_bot': deducted_balance
                    }
                    context.user_data['temp_phone_for_login'] = phone_for_hesda_retry
                    context.user_data['current_login_provider'] = 'hesda'
                    context.user_data['next'] = 'handle_login_otp_input'
                    context.user_data['resume_hesda_purchase_after_otp'] = True
                    await request_otp_and_prompt_hesda(update, context, phone_for_hesda_retry)
                    return                              

                asyncio.create_task(execute_single_purchase_hesda(update, context, user_id, package_id_or_code, package_name, phone, access_token_hesda, payment_method, deducted_balance, return_menu_callback_data))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logging.error(f"Error decoding retry payload for user {user_id}, data: {data}. Error: {e}", exc_info=True)
            await context.bot.send_message(user_id, "❌ Terjadi kesalahan saat memproses permintaan coba lagi. Data tidak valid. Silakan coba beli dari awal.")
            await send_main_menu(update, context)
        except Exception as e:
            logging.error(f"Unexpected error during retry for user {user_id}, data: {data}. Error: {e}", exc_info=True)
            await context.bot.send_message(user_id, "❌ Terjadi kesalahan tak terduga saat mencoba lagi. Silakan coba beli dari awal.")
            await send_main_menu(update, context)
        finally:
                                                                   
            if full_context_key in context.bot_data:
                del context.bot_data[full_context_key]
                logging.info(f"Deleted temporary retry data for key: {full_context_key}")
        return

                                                         
    if not (data.startswith('admin_top_up_confirm_') 
            or data.startswith('admin_top_up_reject_') 
            or data.startswith('admin_user_balance_page_')
            or data.startswith('broadcast_add_button_')
            or data.startswith('broadcast_add_reply_')
            ):
        await query.answer()
                                                                  
        if not (data.startswith('admin_next_api_package_page') or 
                data.startswith('admin_prev_api_package_page') or 
                data == 'admin_back_to_menu'):
            await delete_last_message(user_id, context)
    else:
        await query.answer()


    if data == 'admin_add_balance':
        msg = await context.bot.send_message(user_id, "Masukkan ID User dan jumlah saldo yang ingin ditambahkan (contoh: `123456789 10000`):", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_add_balance_input'
    elif data == 'admin_deduct_balance':
        msg = await context.bot.send_message(user_id, "Masukkan ID User dan jumlah saldo yang ingin dikurangi (contoh: `123456789 5000`):", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_deduct_balance_input'
    elif data == 'admin_block_user_menu':
        msg = await context.bot.send_message(user_id, "Masukkan ID User yang ingin diblokir:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_block_user_input'
    elif data == 'admin_unblock_user_menu':
        msg = await context.bot.send_message(user_id, "Masukkan ID User yang ingin dibatalkan blokirnya:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_unblock_user_input'
    
    elif data == 'admin_broadcast':
        msg = await context.bot.send_message(user_id, "Kirim pesan, foto, atau media lain yang ingin Anda broadcast ke semua user. Pesan ini akan dikirim persis seperti yang Anda kirimkan:")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_broadcast_message_content'
    
    elif data.startswith('admin_toggle_method_'):
        await admin_toggle_payment_method(update, context)
    elif data == 'admin_save_custom_package':
        await admin_save_custom_package(update, context)
    
    elif data == 'admin_search_user_menu':
        msg = await context.bot.send_message(user_id, "Masukkan nama depan atau username user yang ingin dicari:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_search_user_input'
    elif data == 'admin_check_user_transactions_menu':
        msg = await context.bot.send_message(user_id, "Masukkan nama depan atau username user yang riwayat transaksinya ingin dicek:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_check_user_transactions_input'
    elif data == 'admin_check_api_packages':
        await admin_check_api_packages(update, context)
    elif data == 'admin_search_api_package_menu':
        msg = await context.bot.send_message(user_id, "Masukkan kata kunci (nama paket atau kode paket) untuk mencari paket:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'admin_handle_search_api_package_input'
    elif data == 'admin_add_custom_package':
        await admin_add_custom_package_code(update, context)
    elif data == 'admin_edit_custom_package_menu':
        await admin_edit_custom_package_menu(update, context)
    elif data == 'admin_check_user_balances':
        await admin_check_user_balances(update, context, page=0)
    elif data == 'admin_list_users':
        await admin_list_users(update, context, page=0)
    elif data.startswith('admin_list_users_page_'):
        page = int(data.split('_')[-1])
        await admin_list_users(update, context, page=page)
    elif data.startswith('admin_user_balance_page_'):
        page = int(data.split('_')[-1])
        await admin_check_user_balances(update, context, page=page)
    elif data.startswith('admin_edit_package_'):
        package_code = data.replace('admin_edit_package_', '')
        await admin_prompt_edit_custom_package(update, context, package_code)
    elif data.startswith('admin_delete_package_'):
        package_code = data.replace('admin_delete_package_', '')
        await admin_confirm_delete_custom_package(update, context, package_code)
    elif data == 'admin_back_to_menu':
        await admin_menu(update, context)
    elif data.startswith('admin_top_up_confirm_'):
        await admin_confirm_user_top_up(update, context)
    elif data.startswith('admin_top_up_reject_'):
        await admin_reject_user_top_up(update, context)
    elif data.startswith('admin_tx_page_'):
        page = int(data.split('_')[-1])
        await admin_display_user_transactions(update, context, page=page)
        return
    elif data == 'admin_next_api_package_page':
        await admin_next_api_package_page(update, context)
        return
    elif data == 'admin_prev_api_package_page':
        await admin_prev_api_package_page(update, context)
        return
                        
async def admin_edit_custom_package_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    custom_packages = user_data.get("custom_packages", {})

    if not custom_packages:
        await context.bot.send_message(user_id_admin, "Belum ada paket kustom yang bisa diedit atau dihapus.")
        await admin_menu(update, context)
        return

    text = "*Pilih Paket Kustom untuk Diedit/Dihapus:*\n\n"
    keyboard = []
    for code, details in custom_packages.items():
        name = details.get('name', 'N/A')
        price = details.get('price', 'N/A')
        text += f"• *{name}* (Kode: `{code}`, Harga: Rp{price:,})\n"
        keyboard.append([
            InlineKeyboardButton(f"✏️ Edit {name}", callback_data=f"admin_edit_package_{code}"),
            InlineKeyboardButton(f"🗑️ Hapus {name}", callback_data=f"admin_delete_package_{code}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan admin_edit_custom_package_menu: {e}. Mengirim pesan baru.")
        await context.bot.send_message(user_id_admin, text, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_prompt_edit_custom_package(update: Update, context: ContextTypes.DEFAULT_TYPE, package_code: str):
    user_id_admin = update.effective_user.id
    package_details = user_data["custom_packages"].get(package_code)

    if not package_details:
        await context.bot.send_message(user_id_admin, "Paket kustom tidak ditemukan.")
        await admin_menu(update, context)
        return
    
    context.user_data['editing_package_code'] = package_code
    text = (f"Anda akan mengedit paket `{package_code}` (Nama: *{package_details['name']}*, Harga: Rp{package_details['price']:,}).\n\n"
            "Ketik nama baru untuk paket ini atau ketik `SKIP` untuk tidak mengubah nama:")
    
    await context.bot.send_message(user_id_admin, text, parse_mode="Markdown")
    context.user_data['next'] = 'admin_edit_custom_package_name_input'

async def admin_confirm_delete_custom_package(update: Update, context: ContextTypes.DEFAULT_TYPE, package_code: str):
    user_id_admin = update.effective_user.id
    package_details = user_data["custom_packages"].get(package_code)

    if not package_details:
        await context.bot.send_message(user_id_admin, "Paket kustom tidak ditemukan.")
        await admin_menu(update, context)
        return
    
    text = (f"Anda yakin ingin menghapus paket kustom:\n"
            f"*Nama*: {package_details['name']}\n"
            f"*Kode*: `{package_code}`\n"
            f"*Harga*: Rp{package_details['price']:,}\n\n"
            "Tekan `YA` untuk konfirmasi, atau `TIDAK` untuk membatalkan.")
    
    context.user_data['confirm_delete_package_code'] = package_code
    await context.bot.send_message(user_id_admin, text, parse_mode="Markdown")
    context.user_data['next'] = 'admin_handle_delete_custom_package_confirmation'

def extract_package_display_name(package_full_name: str) -> str:
    match1 = re.search(r'\]\s*(.*?)(?:\s*\(|$)', package_full_name)
    if match1:
        extracted = match1.group(1).strip()
        if extracted:
            return extracted

    if package_full_name.startswith("[Method E-Wallet]"):
        parts = package_full_name.split("]", 1)
        if len(parts) > 1:
            name_part = parts[1].split("(", 1)[0].strip()
            if name_part:
                return name_part
        return package_full_name.replace("[Method E-Wallet]", "").split("(", 1)[0].strip()

    cleaned_name = re.sub(r'\[.*?\]', '', package_full_name)
    cleaned_name = re.sub(r'\(.*?\)', '', cleaned_name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    
    if cleaned_name:
        return cleaned_name
    
    return package_full_name


async def admin_check_api_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    logging.info(f"Admin {user_id_admin} meminta daftar paket API.")
    try:
        response = requests.get(f"https://golang-openapi-packagelist-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}")
        response.raise_for_status()
        paket_data = response.json().get("data", [])
        
        context.user_data['all_api_packages'] = paket_data
        
        page = 0
        context.user_data['api_package_current_page'] = page
        
        per_page = PACKAGES_PER_PAGE_ADMIN
        start = page * per_page
        end = start + per_page
        sliced = paket_data[start:end]

        logging.debug(f"Initial load: total packages: {len(paket_data)}, page: {page}, slice: {start}-{end}")

        if not sliced:
            response_text = "Tidak ada data paket dari API tersedia."
        else:
            response_text = "*Daftar Paket dari API:*\n\n"
            for i, paket in enumerate(sliced):
                full_name = paket.get("package_name", "Tanpa Nama")
                display_name = extract_package_display_name(full_name)
                code = paket.get("package_code", "-")
                price = paket.get("package_harga", "N/A")
                response_text += f"{i+1+start}. *{display_name}*\n"
                response_text += f"   Kode: `{code}`\n"
                response_text += f"   Harga: `Rp{price}`\n\n"
            
        buttons = []
        nav_buttons = []
        if end < len(paket_data):
            nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="admin_next_api_package_page"))
        
        nav_buttons.append(InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu"))
        buttons.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(buttons)
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)
            except Exception as e:
                logging.warning(f"Gagal mengedit pesan admin_check_api_packages: {e}. Mengirim pesan baru.")
                await context.bot.send_message(user_id_admin, response_text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await context.bot.send_message(user_id_admin, response_text, parse_mode="Markdown", reply_markup=reply_markup)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error saat mengambil daftar paket API untuk admin: {e}")
        await context.bot.send_message(user_id_admin, "Terjadi kesalahan saat mengambil daftar paket dari API. Mohon coba lagi nanti.")
        await admin_menu(update, context)
    except json.JSONDecodeError:
        logging.error(f"Gagal mengurai JSON dari daftar paket API untuk admin. Respon: {response.text}")
        await context.bot.send_message(user_id_admin, "Terjadi kesalahan saat memproses data paket dari API.")
        await admin_menu(update, context)

async def admin_next_api_package_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    query = update.callback_query
    await query.answer()

    paket_data = context.user_data.get("all_api_packages", [])
    if not paket_data:
        await context.bot.send_message(user_id_admin, "Tidak ada data paket yang dimuat. Silakan coba 'Cek & Kelola Paket API' lagi.")
        return

    page = context.user_data.get("api_package_current_page", 0) + 1
    
    per_page = PACKAGES_PER_PAGE_ADMIN
    start = page * per_page
    end = start + per_page
    sliced = paket_data[start:end]

    logging.debug(f"Next page: total packages: {len(paket_data)}, current page: {page}, slice: {start}-{end}")

    if not sliced:
        await query.answer("Anda sudah di halaman terakhir.", show_alert=True)
        return

    context.user_data['api_package_current_page'] = page

    response_text = "*Daftar Paket dari API:*\n\n"
    for i, paket in enumerate(sliced):
        full_name = paket.get("package_name", "Tanpa Nama")
        display_name = extract_package_display_name(full_name)
        code = paket.get("package_code", "-")
        price = paket.get("package_harga", "N/A")
        response_text += f"{i+1+start}. *{display_name}*\n"
        response_text += f"   Kode: `{code}`\n"
        response_text += f"   Harga: `Rp{price}`\n\n"
        
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏪ Prev", callback_data="admin_prev_api_package_page"))
    if end < len(paket_data):
        nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="admin_next_api_package_page"))
    nav_buttons.append(InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu"))
    buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan admin_next_api_package_page: {e}. Mengirim pesan baru.")
        await context.bot.send_message(user_id_admin, response_text, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_prev_api_package_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    query = update.callback_query
    await query.answer()

    paket_data = context.user_data.get("all_api_packages", [])
    if not paket_data:
        await context.bot.send_message(user_id_admin, "Tidak ada data paket yang dimuat. Silakan coba 'Cek & Kelola Paket API' lagi.")
        return

    page = max(0, context.user_data.get("api_package_current_page", 0) - 1)
    per_page = PACKAGES_PER_PAGE_ADMIN
    start = page * per_page
    end = start + per_page
    sliced = paket_data[start:end]

    logging.debug(f"Previous page: total packages: {len(paket_data)}, current page: {page}, slice: {start}-{end}")

    if not sliced and page > 0:
        await query.answer("Anda sudah di halaman pertama.", show_alert=True)
        return

    context.user_data['api_package_current_page'] = page

    response_text = "*Daftar Paket dari API:*\n\n"
    for i, paket in enumerate(sliced):
        full_name = paket.get("package_name", "Tanpa Nama")
        display_name = extract_package_display_name(full_name)
        code = paket.get("package_code", "-")
        price = paket.get("package_harga", "N/A")
        response_text += f"{i+1+start}. *{display_name}*\n"
        response_text += f"   Kode: `{code}`\n"
        response_text += f"   Harga: `Rp{price}`\n\n"
        
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏪ Prev", callback_data="admin_prev_api_package_page"))
    if end < len(paket_data):
        nav_buttons.append(InlineKeyboardButton("⏩ Next", callback_data="admin_next_api_package_page"))
    nav_buttons.append(InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu"))
    buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logging.warning(f"Gagal mengedit pesan admin_prev_api_package_page: {e}. Mengirim pesan baru.")
        await context.bot.send_message(user_id_admin, response_text, parse_mode="Markdown", reply_markup=reply_markup)

async def admin_handle_search_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    search_query = update.message.text.strip()                          
    found_users = []

    if search_query.isdigit() and search_query in user_data["registered_users"]:
        details = user_data["registered_users"][search_query]
        found_users.append(f"• ID: `{search_query}`\n  Nama: `{details.get('first_name', 'N/A')}`\n  Username: `@{details.get('username', 'N/A')}`\n  Saldo: `Rp{details.get('balance', 0):,}`")
    
    else:
        search_query_lower = search_query.lower()
        for uid_str, details in user_data["registered_users"].items():
            first_name = details.get('first_name', '').lower()
            username = details.get('username', '').lower()
            
            if search_query_lower in first_name or search_query_lower in username:
                found_users.append(f"• ID: `{uid_str}`\n  Nama: `{details.get('first_name', 'N/A')}`\n  Username: `@{details.get('username', 'N/A')}`\n  Saldo: `Rp{details.get('balance', 0):,}`")

    response_text_parts = []
    if found_users:
        response_text_parts.append("*Hasil Pencarian User:*\n" + "\n".join(found_users))
    else:
        response_text_parts.append(f"❌ Tidak ada user ditemukan dengan query '{search_query}'.")

    keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("\n".join(response_text_parts), parse_mode="Markdown", reply_markup=reply_markup)

async def admin_handle_search_api_package_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    search_query = update.message.text.strip().lower()
    all_packages = context.user_data.get('all_api_packages', [])

    if not all_packages:
        await update.message.reply_text("Data paket API belum dimuat. Silakan gunakan menu 'Cek & Kelola Paket API' terlebih dahulu.")
        await admin_menu(update, context)
        return

    found_packages = []
    for paket in all_packages:
        name = paket.get("package_name", "").lower()
        description = paket.get("package_description", "").lower()
        code = paket.get("package_code", "").lower()
        
        if search_query in name or search_query in description or search_query in code:
            found_packages.append(paket)
    
    response_text_parts = []
    if found_packages:
        response_text_parts.append(f"*Hasil Pencarian Paket untuk '{search_query}':*\n")
        for i, paket in enumerate(found_packages):
            full_name = paket.get("package_name", "Tanpa Nama")
            display_name = extract_package_display_name(full_name)
            code = paket.get("package_code", "-")
            price = paket.get("package_harga", "N/A")
            response_text_parts.append(f"{i+1}. *{display_name}*\n")
            response_text_parts.append(f"   Kode: `{code}`\n")
            response_text_parts.append(f"   Harga: `Rp{price}`\n")
    else:
        response_text_parts.append(f"❌ Tidak ada paket ditemukan dengan kata kunci '{search_query}'.")

    keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("\n".join(response_text_parts), parse_mode="Markdown", reply_markup=reply_markup)


async def admin_handle_check_user_transactions_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    search_query = update.message.text.strip()
    
    found_user_id = None
    user_info = None

                                   
    if search_query.isdigit() and search_query in user_data["registered_users"]:
        found_user_id = search_query
        user_info = user_data["registered_users"][search_query]
    else:
                                                             
        search_query_lower = search_query.lower()
        if isinstance(user_data.get("registered_users"), dict):
            for uid_str, details in user_data["registered_users"].items():
                first_name = details.get('first_name', '').lower()
                username = details.get('username', '').lower()
                
                if search_query_lower in first_name or search_query_lower in username:
                    found_user_id = uid_str
                    user_info = details
                    break
    
    if found_user_id and user_info:
                                              
        context.user_data['current_viewed_transactions_user_id'] = found_user_id
        await admin_display_user_transactions(update, context, page=0)                    
    else:
        response_text = "❌ User tidak ditemukan. Pastikan ID, nama depan, atau username benar."
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response_text, reply_markup=reply_markup, parse_mode="Markdown")

async def admin_handle_add_balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    try:
        parts = update.message.text.split()
        target_user_id = int(parts[0])
        amount = int(parts[1])
        
        if str(target_user_id) not in user_data["registered_users"]:
            user_data["registered_users"][str(target_user_id)] = {
                "accounts": {}, 
                "balance": 0,
                "first_name": "N/A",
                "username": "N/A",
                "transactions": [],
                "selected_hesdapkg_ids": []                                   
            }
            await update.message.reply_text(f"User ID `{target_user_id}` belum terdaftar, telah didaftarkan dengan saldo 0.")

        user_data["registered_users"][str(target_user_id)]["balance"] += amount
        user_data["registered_users"][str(target_user_id)]["transactions"].append({
            "type": "Top Up Manual Admin",
            "amount": amount,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "admin_id": user_id_admin,
            "status": "Berhasil"
        })
        simpan_data_ke_db()
        await update.message.reply_text(f"✅ Saldo user `{target_user_id}` berhasil ditambahkan sebesar `Rp{amount:,}`. Saldo baru: `Rp{user_data['registered_users'][str(target_user_id)]['balance']:,}`.", parse_mode="Markdown")
        try:
            await context.bot.send_message(target_user_id, f"💰 Saldo Anda telah ditambahkan sebesar *Rp{amount:,}* oleh admin. Saldo Anda sekarang: *Rp{user_data['registered_users'][str(target_user_id)]['balance']:,}*.", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Gagal mengirim notifikasi saldo ke user {target_user_id}: {e}")
            await update.message.reply_text(f"⚠️ Gagal mengirim notifikasi ke user `{target_user_id}`.", parse_mode="Markdown")
    except (ValueError, IndexError):
        await update.message.reply_text("Format salah. Gunakan: `ID_User Jumlah_Saldo` (contoh: `123456789 10000`)", parse_mode="Markdown")
    finally:
        await admin_menu(update, context)

async def admin_handle_deduct_balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    try:
        parts = update.message.text.split()
        target_user_id = int(parts[0])
        amount = int(parts[1])

        if str(target_user_id) not in user_data["registered_users"]:
            await update.message.reply_text(f"❌ User ID `{target_user_id}` tidak terdaftar.", parse_mode="Markdown")
            return

        user_data["registered_users"][str(target_user_id)]["balance"] -= amount
        user_data["registered_users"][str(target_user_id)]["transactions"].append({
            "type": "Kurangi Saldo Manual Admin",
            "amount": -amount,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "admin_id": user_id_admin,
            "status": "Info"
        })
        simpan_data_ke_db()
        await update.message.reply_text(f"✅ Saldo user `{target_user_id}` berhasil dikurangi sebesar `Rp{amount:,}`. Saldo baru: `Rp{user_data['registered_users'][str(target_user_id)]['balance']:,}`.", parse_mode="Markdown")
        try:
            await context.bot.send_message(target_user_id, f"💸 Saldo Anda telah dikurangi sebesar *Rp{amount:,}* oleh admin. Saldo Anda sekarang: *Rp{user_data['registered_users'][str(target_user_id)]['balance']:,}*.", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Gagal mengirim notifikasi saldo ke user {target_user_id}: {e}")
            await update.message.reply_text(f"⚠️ Gagal mengirim notifikasi ke user `{target_user_id}`.", parse_mode="Markdown")
    except (ValueError, IndexError):
        await update.message.reply_text("Format salah. Gunakan: `ID_User Jumlah_Saldo` (contoh: `123456789 5000`)", parse_mode="Markdown")
    finally:
        await admin_menu(update, context)

async def admin_handle_block_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    try:
        user_to_block = int(update.message.text.strip())
        if user_to_block == ADMIN_ID:
            await update.message.reply_text("Anda tidak bisa memblokir diri sendiri!")
            return
        
        if user_to_block not in user_data["blocked_users"]:
            user_data["blocked_users"].append(user_to_block)
            if str(user_to_block) in user_data["registered_users"]:
                del user_data["registered_users"][str(user_to_block)]
            simpan_data_ke_db()
            await update.message.reply_text(f"❌ User ID `{user_to_block}` berhasil diblokir dan datanya dihapus.", parse_mode="Markdown")
            try:
                await context.bot.send_message(user_to_block, "⛔ Anda telah diblokir dan tidak dapat lagi menggunakan bot ini. Silakan hubungi admin jika Anda merasa ini adalah kesalahan.")
            except Exception as e:
                logging.warning(f"Gagal mengirim notifikasi blokir ke user {user_to_block}: {e}")
        else:
            await update.message.reply_text(f"User ID `{user_to_block}` sudah diblokir.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("User ID harus berupa angka.")
    finally:
        await admin_menu(update, context)

async def admin_handle_unblock_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    try:
        user_to_unblock = int(update.message.text.strip())
        if user_to_unblock in user_data["blocked_users"]:
            user_data["blocked_users"].remove(user_to_unblock)
            if str(user_to_unblock) not in user_data["registered_users"]:
                user_data["registered_users"][str(user_to_unblock)] = {
                    "accounts": {}, 
                    "balance": 0,
                    "first_name": "N/A",
                    "username": "N/A",
                    "transactions": [],
                    "selected_hesdapkg_ids": []                                 
                }
            simpan_data_ke_db()
            await update.message.reply_text(f"✅ User ID `{user_to_unblock}` berhasil dibatalkan blokirnya.", parse_mode="Markdown")
            try:
                await context.bot.send_message(user_to_unblock, "🔓 Blokir Anda telah dicabut. Anda sekarang dapat menggunakan bot ini kembali. Silakan ketik `/start`.")
            except Exception as e:
                logging.warning(f"Gagal mengirim notifikasi unblock ke user {user_to_unblock}: {e}")
        else:
            await update.message.reply_text(f"User ID `{user_to_unblock}` tidak ditemukan di daftar yang diblokir.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("User ID harus berupa angka.")
    finally:
        await admin_menu(update, context)

async def admin_add_custom_package_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    await context.bot.send_message(user_id_admin, "Masukkan Kode Paket dari API KMSP:")
    context.user_data['next'] = 'admin_handle_smart_package_code_input'

async def admin_handle_smart_package_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    code = update.message.text.strip()

    if code in user_data["custom_packages"]:
        await update.message.reply_text(f"❌ Kode `{code}` sudah ada di database paket kustom. Gunakan kode lain atau edit yang sudah ada.")
        context.user_data['next'] = 'admin_handle_smart_package_code_input'
        return
    
    status_msg = await update.message.reply_text(f"🔍 Mencari detail untuk `{code}` dari API...")
    
    api_details = await get_api_package_details(code)
    
    if not api_details:
        await status_msg.edit_text(f"❌ Kode paket `{code}` tidak ditemukan di API KMSP. Pastikan kode sudah benar.")
        context.user_data['next'] = 'admin_handle_smart_package_code_input'
        return

    api_name = api_details.get("package_name", "Nama Tidak Ditemukan")
    api_methods = [method['payment_method'] for method in api_details.get("available_payment_methods", [])]

    final_methods = []
    if "BALANCE" in api_methods:
        final_methods.append("BALANCE")
    if "DANA" in api_methods:
        final_methods.append("DANA")
    if "QRIS" in api_methods:
        final_methods.append("QRIS")

    context.user_data['temp_custom_pkg'] = {
        'code': code,
        'name': api_name,
        'payment_methods': final_methods
    }
    
    await status_msg.edit_text(
        f"✅ Paket ditemukan: *{api_name}*\n\n"
        f"Sekarang, masukkan *Nama Tampilan* singkat untuk paket ini (contoh: `iFlix Tanpa Gandengan`):",
        parse_mode="Markdown"
    )
    context.user_data['next'] = 'admin_handle_smart_package_display_name_input' 

async def admin_handle_smart_package_display_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    display_name = update.message.text.strip()
    context.user_data['temp_custom_pkg']['name'] = display_name
    
    await update.message.reply_text(
        f"✅ Nama tampilan diterima: *{display_name}*.\n\n"
        f"Sekarang, masukkan *harga jual* di bot Anda (contoh: `1500`):",
        parse_mode="Markdown"
    )
    context.user_data['next'] = 'admin_handle_smart_package_price_input'

async def admin_handle_smart_package_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.strip())
        context.user_data['temp_custom_pkg']['price'] = price
        await update.message.reply_text(
            f"✅ Harga Jual `Rp{price:,}` diterima.\n\n"
            f"Selanjutnya, masukkan *Price or fee* pastikan price nya sama dengan harga dari KMSP (Contoh: `1500` untuk iFlix). Masukkan `0` jika tidak ada.",
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'admin_handle_smart_package_ewallet_fee_input'
    except ValueError:
        await update.message.reply_text("❌ Harga tidak valid. Masukkan angka saja.")
        context.user_data['next'] = 'admin_handle_smart_package_price_input'

async def admin_handle_smart_package_ewallet_fee_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ewallet_fee = int(update.message.text.strip())
        context.user_data['temp_custom_pkg']['ewallet_fee'] = ewallet_fee
        await update.message.reply_text(
            f"✅ Biaya E-Wallet `Rp{ewallet_fee:,}` diterima.\n\n"
            f"Terakhir, masukkan deskripsi singkat untuk paket ini:",
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'admin_handle_smart_package_desc_and_save'
    except ValueError:
        await update.message.reply_text("❌ Biaya E-Wallet tidak valid. Masukkan angka saja.")
        context.user_data['next'] = 'admin_handle_smart_package_ewallet_fee_input'
        
async def admin_handle_smart_package_desc_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pkg_data = context.user_data.pop('temp_custom_pkg', None)
    pkg_data['description'] = update.message.text.strip()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO custom_packages (code, name, price, description, payment_methods, ewallet_fee)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        pkg_data['code'],
        pkg_data['name'],
        pkg_data['price'],
        pkg_data['description'],
        json.dumps(pkg_data['payment_methods']),
        pkg_data.get('ewallet_fee', 0)
    ))
    conn.commit()
    conn.close()
    
    muat_data_dari_db()

    await update.message.reply_text(f"🎉 Paket kustom *{pkg_data['name']}* berhasil disimpan!", parse_mode="Markdown")
    await admin_menu(update, context)

async def show_custom_package_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    package_code = query.data.replace("view_custom_package_", "")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, description, payment_methods FROM custom_packages WHERE code = ?", (package_code,))
    package = cursor.fetchone()
    conn.close()

    if not package:
        await query.answer("Paket tidak ditemukan.", show_alert=True)
        return

    name, price, description, methods_json = package
    available_methods = json.loads(methods_json or '[]')

    text = (
        f"*{name.upper()}*\n\n"
        f"_{description}_\n\n"
        f"*Harga:* `Rp{price:,}`\n\n"
        "Silakan pilih metode pembayaran:"
    )

    keyboard = []
    payment_buttons = []
    if "DANA" in available_methods:
        payment_buttons.append(InlineKeyboardButton("DANA", callback_data=f"buy_custom_{package_code}_DANA"))
    if "QRIS" in available_methods:
        payment_buttons.append(InlineKeyboardButton("QRIS", callback_data=f"buy_custom_{package_code}_QRIS"))
    if "BALANCE" in available_methods:
        payment_buttons.append(InlineKeyboardButton("BELI", callback_data=f"buy_custom_{package_code}_BALANCE"))
    
    if payment_buttons:
        keyboard.append(payment_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="show_custom_packages")])
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_custom_package_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    prefix_dan_kode, payment_method = query.data.rsplit('_', 1)
    package_code = prefix_dan_kode.replace('buy_custom_', '', 1)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM custom_packages WHERE code = ?", (package_code,))
    package = cursor.fetchone()
    conn.close()

    if not package:
        await query.answer("Paket tidak ditemukan.", show_alert=True)
        return
        
    package_name, package_price = package
    user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

    if user_balance < package_price:
        await query.answer(f"Saldo bot Anda tidak cukup (butuh Rp{package_price:,})", show_alert=True)
        return
    
    context.user_data['selected_custom_package_code'] = package_code
    context.user_data['selected_custom_package_name'] = package_name
    context.user_data['selected_custom_package_price'] = package_price
    context.user_data['selected_custom_payment_method'] = payment_method
    
    await query.edit_message_text(
        f"Anda memilih: *{package_name}* ({payment_method}).\nMasukkan nomor HP untuk pembelian:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"view_custom_package_{package_code}")]]))
        
    context.user_data['next'] = 'handle_buy_custom_package_phone_input'

async def do_broadcast(context: ContextTypes.DEFAULT_TYPE, admin_chat_id: int, message_to_copy: Message, add_admin_button: bool, add_reply_button: bool, excluded_users: list):
    success_count = 0
    fail_count = 0
    
    buttons = []
    if add_reply_button:
        buttons.append(InlineKeyboardButton("✍️ Jawab", callback_data="user_reply_to_broadcast"))
    if add_admin_button:
        buttons.append(InlineKeyboardButton("💬 Hubungi Admin", url=f"https://t.me/{ADMIN_USERNAME}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    excluded_ids = set()
    for user_identifier in excluded_users:
        if user_identifier.isdigit():
            excluded_ids.add(int(user_identifier))
        else:
            username_to_find = user_identifier.lower().replace('@', '')
            for uid, details in user_data["registered_users"].items():
                if details.get('username', 'N/A').lower() == username_to_find:
                    excluded_ids.add(int(uid))
                    break
    
    logging.info(f"Broadcast akan dijalankan. Tombol Admin: {add_admin_button}, Tombol Jawab: {add_reply_button}. Pengecualian ID: {excluded_ids}")
    all_user_ids = list(user_data["registered_users"].keys())
    
    for uid_str in all_user_ids:
        try:
            target_user_id = int(uid_str)
            if target_user_id == admin_chat_id or target_user_id in excluded_ids:
                continue

            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=message_to_copy.chat_id,
                message_id=message_to_copy.message_id,
                reply_markup=reply_markup
            )
            success_count += 1
            logging.info(f"Broadcast berhasil dikirim ke {target_user_id}")
        except Exception as e:
            logging.warning(f"Gagal mengirim broadcast ke user {uid_str}: {e}")
            fail_count += 1
        
        await asyncio.sleep(0.1) 
    
    final_message = f"✅ Selesai mengirim broadcast.\nBerhasil: *{success_count}* user\nGagal: *{fail_count}* user"
    await context.bot.send_message(admin_chat_id, final_message, parse_mode="Markdown")

async def admin_handle_broadcast_message_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return

    context.user_data['broadcast_message_to_copy'] = update.message
    
    keyboard = [
        [InlineKeyboardButton("Ya, Tambahkan", callback_data="broadcast_add_button_yes")],
        [InlineKeyboardButton("Tidak, Lanjutkan", callback_data="broadcast_add_button_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Pesan untuk broadcast telah disimpan. Apakah Anda ingin menambahkan tombol 'Hubungi Admin' di bawah pesan broadcast?",
        reply_markup=reply_markup
    )

async def admin_handle_broadcast_button_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()

    add_button = (query.data == 'broadcast_add_button_yes')
    context.user_data['broadcast_add_admin_button'] = add_button

    keyboard = [
        [InlineKeyboardButton("Ya, Tambahkan Tombol 'Jawab'", callback_data="broadcast_add_reply_yes")],
        [InlineKeyboardButton("Tidak, Lanjutkan Saja", callback_data="broadcast_add_reply_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Oke. Sekarang, apakah Anda ingin menambahkan tombol 'Jawab' agar user bisa membalas broadcast ini?",
        reply_markup=reply_markup
    )

async def admin_handle_broadcast_reply_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete() 

    add_reply_button = (query.data == 'broadcast_add_reply_yes')
    context.user_data['broadcast_add_reply_button'] = add_reply_button
    
    reply_choice_text = "DITAMBAHKAN" if add_reply_button else "TIDAK ditambahkan"

    msg = await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"Baik, tombol 'Jawab' akan *{reply_choice_text}*.\n"
             "Terakhir, masukkan ID atau Username user yang ingin *DIKECUALIKAN* dari broadcast ini, pisahkan dengan spasi.\n"
             "Contoh: `12345 @usernameLain 67890`\n"
             "Kirim `TIDAK ADA` jika ingin mengirim ke semua user.",
        parse_mode="Markdown"
    )
    bot_messages.setdefault(query.from_user.id, []).append(msg.message_id)
    context.user_data['next'] = 'admin_handle_broadcast_exclusions'


async def admin_handle_broadcast_exclusions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if user_id_admin != ADMIN_ID: return
    
    message_to_copy = context.user_data.pop('broadcast_message_to_copy', None)
    add_admin_button = context.user_data.pop('broadcast_add_admin_button', False)
    add_reply_button = context.user_data.pop('broadcast_add_reply_button', False)
    
    if not message_to_copy:
        await update.message.reply_text("Terjadi kesalahan, pesan untuk broadcast tidak ditemukan. Silakan ulangi dari menu admin.")
        await admin_menu(update, context)
        return

    excluded_input = update.message.text.strip()
    excluded_users = []
    if excluded_input.upper() != 'TIDAK ADA':
        excluded_users = excluded_input.split()
    
    await update.message.reply_text(
        f"🚀 Memulai proses broadcast ke user terdaftar (dengan pengecualian {len(excluded_users)} user)....\n"
        "Bot akan tetap berjalan normal. Anda akan menerima notifikasi setelah selesai.",
        parse_mode="Markdown"
    )
    
    asyncio.create_task(do_broadcast(context, user_id_admin, message_to_copy, add_admin_button, add_reply_button, excluded_users))
    await admin_menu(update, context)

async def send_xcp_addon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    instructional_text = (
    "*Pilih Mode Pembelian XCS Add-On*\n\n"
    "Terdapat dua cara untuk melakukan pembelian:\n\n"
    "1. *Mode Otomatis*"
    "   Secara otomatis membeli semua paket tanpa ribet . Proses lebih cepat dan minim kesalahan.\n\n"
    "2. *Mode Manual*"
    "   Memilih dan membeli paket satu per satu.\n\n"
    "💡 *Rekomendasi:*"
    "Jika baru pertama kali atau ingin proses yang mudah dan juga meminimalisir kegagalan, sangat disarankan untuk memilih mode *Otomatis*."
)

    keyboard = [
        [InlineKeyboardButton("OTOMATIS 🤖", callback_data="automatic_xcs_addon_flow")],                               
        [InlineKeyboardButton("MANUAL ✍️", callback_data="manual_xcs_addon_selection_menu")],                             
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

                                      
async def send_xcp_addon_dana_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
                    
    instructional_text = (
        "Silakan pilih paket Add-On XCP (DANA):"
    )
    
    all_addons_except_xcp8gb = ADD_ON_SEQUENCE 
    
    paket_buttons = []
    for i in range(0, len(all_addons_except_xcp8gb), 2):
        row = []
        pkg1 = all_addons_except_xcp8gb[i]
        row.append(InlineKeyboardButton(pkg1['name'], callback_data=f"xcp_{pkg1['code']}"))
        if i + 1 < len(all_addons_except_xcp8gb):
            pkg2 = all_addons_except_xcp8gb[i+1]
            row.append(InlineKeyboardButton(pkg2['name'], callback_data=f"xcp_{pkg2['code']}"))
        paket_buttons.append(row)

    paket_buttons.append([InlineKeyboardButton("🛒 BELI SEMUA ADD ON (Batch)", callback_data="buy_all_addons")])
    paket_buttons.append([InlineKeyboardButton("🔙 Kembali ke Menu XCS ADD ON", callback_data="xcp_addon")])
    
    reply_markup = InlineKeyboardMarkup(paket_buttons)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        
async def send_uts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    instructional_text = (
    "*Pilih Mode Pembelian XUTS*\n\n"
    "Terdapat dua cara untuk melakukan pembelian:\n\n"
    "1. *Mode Otomatis*"
    "   Secara otomatis membeli semua paket tanpa ribet . Proses lebih cepat dan minim kesalahan.\n\n"
    "2. *Mode Manual*"
    "   Memilih dan membeli paket satu per satu.\n\n"
    "💡 *Rekomendasi:*"
    "Jika baru pertama kali atau ingin proses yang mudah dan juga meminimalisir kegagalan, sangat disarankan untuk memilih mode *Otomatis*."
)

    keyboard = [
        [InlineKeyboardButton("OTOMATIS 🤖", callback_data="automatic_purchase_flow")],
        [InlineKeyboardButton("MANUAL ✍️", callback_data="manual_uts_selection_menu")],                                
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_manual_uts_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    instructional_text = (
        "⚠️ *CARA BELI* ⚠️\n"
        "1.BELI DULU XUTS,WAJIB SEBELUM MEMBELI ( XUTS,XUTP,XCS ) BOT AKAN MENGECEK APAKAH NOMOR NYA COCOK ATAU TIDAK\n"
        "2.JIKA NOMOR TIDAK COCOK,BOT AKAN MEMPROSES AGAR NOMOR NYA COCOK, PROSES 10 MENIT\n"
        "3.SETELAH MENUNGGU 10 MENIT MAKA BELI LAGI XUTS\n"
        "4.SETELAH NOMOR COCOK BELI PAKET XC 1+1GB BAYAR 12.500K\n"
        "5.TUNGGU PAKET XUTS MASUK\n"
        "Silakan pilih paket XC 1+1GB & XUTS yang ingin dibeli:"
    )
    uts_buttons = [
        [InlineKeyboardButton("XUTS", callback_data="buy_uts_pulsa_gandengan")],
        [InlineKeyboardButton("XC 1+1GB DANA", callback_data="buy_uts_1gb")],
        [InlineKeyboardButton("XC 1+1GB PULSA", callback_data="buy_uts_1gb_pulsa")],
        [InlineKeyboardButton("XC 1+1GB QRIS", callback_data="buy_uts_1gb_qris")],
        [InlineKeyboardButton("🔙 Kembali ke Pilihan Mode", callback_data="menu_uts_nested")]                                
    ]
    reply_markup = InlineKeyboardMarkup(uts_buttons)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_xutp_method_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = (
        "Silakan pilih metode pembayaran untuk pembelian *XUTP*:\n\n"
        "Paket awal yang akan di dapat *ADD ON PREMIUM*\n"
        "dan paket kedua yang akan di dapat adalah *XCP 8GB*\n\n"
        "*⚠️ PERHATIAN ⚠️*\n"
        "Jika ingin add on nya bukan cuma *PREMIUM* bisa pergi ke menu *XCS ADD ON* agar bisa memilih lebih dari 1 add on"
    )
    keyboard = [
        [InlineKeyboardButton("DANA", callback_data="xutp_method_dana")],
        [InlineKeyboardButton("PULSA", callback_data="xutp_method_pulsa")],
        [InlineKeyboardButton("QRIS", callback_data="xutp_method_qris")],
        [InlineKeyboardButton("🔙 Kembali ke Menu Tembak Paket", callback_data="tembak_paket")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_manual_xcs_addon_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    instructional_text = (
        "⚠️ *CARA BELI XCS ADD ON MANUAL* ⚠️\n"
        "1. Pastikan Sudah beli XUTS di menu XC 1+1 GB & XUTS agar nomor nya suport untuk semua paket,jika belum maka harus beli DULU KARNA WAJIB agar nantinya XUT versi 30h masuk❗\n"
        "2. Beli Add-On satu per satu di menu atau Bypas V1 atau V2 sama saja\n"
        "3. menu bypas V1&V2 gak ada bedanya keunggulan V2 CUKUP SATU KALI OTP gak perlu otp BYPAS\n"
        "4. Setelah semua Add-On berhasil, beli 'XCP 8GB'. memototong saldo bot 5k.\n"
        "5. Tunggu semua paket masuk ke nomor Anda.\n"
        "Silakan pilih menu pembelian paket XCP ADD ON atau BYPAS:"
    )
    
    keyboard = [
        [InlineKeyboardButton("BYPAS V1", callback_data="menu_bypass_nested")],
        [InlineKeyboardButton("BYPAS V2", callback_data="menu_30h_nested")],
        [InlineKeyboardButton("XCP 8GB DANA", callback_data=f"xcp_{XCP_8GB_PACKAGE['code']}")],
        [InlineKeyboardButton("XCP 8GB PULSA", callback_data=f"xcp_{XCP_8GB_PULSA_PACKAGE['code']}")],
        [InlineKeyboardButton("XCP 8GB QRIS", callback_data=f"xcp_{XCP_8GB_PACKAGE['code']}_QRIS")],
        [InlineKeyboardButton("🔙 Kembali ke Pilihan Mode XCS", callback_data="xcp_addon")]                                 
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, instructional_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_automatic_xcs_addon_method_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
                                      
    message_text = (
        "⚠️ *HARAP BACA* ⚠️\n\n"
        "Pastikan membeli paket XCS ADD ON ini di awal jam ideal nya di bawah menit 40 contoh nya pada jam 7.12 atau 9.33 intinya mah jangan di atas menit 40\n"
        "Karna proses pembelian paket untuk beberapa nomor yang di suruh nunggu 10 menit itu lama jika sudah masuk ke jam berikutnya bisa bisa add on nya tidak masuk.\n"
        "*Segala Konsekwensinya di tanggung user non garansi no refund*\n\n"
        "Silakan pilih metode pembayaran untuk pembelian paket XCS ADD ON Otomatis:"
    )
                             

    keyboard = [
        [InlineKeyboardButton("DANA", callback_data="auto_xcs_method_dana")],
        [InlineKeyboardButton("PULSA", callback_data="auto_xcs_method_pulsa")],
        [InlineKeyboardButton("QRIS", callback_data="auto_xcs_method_qris")],
        [InlineKeyboardButton("🔙 Kembali ke Pilihan Mode XCS", callback_data="xcp_addon")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_automatic_xcs_addon_package_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_method_for_xcp_8gb = context.user_data.get('automatic_xcs_payment_method')

    text = (
        f"*Mode Otomatis: Pilih Paket XCS ADD ON (Pembayaran XCP 8GB: {payment_method_for_xcp_8gb})*\n\n"
        "Pilih paket ADD ON yang ingin Anda beli. Anda bisa memilih lebih dari satu.\n"
        "Setelah selesai, tekan 'LANJUT' untuk memproses."
    )

                                                                  
    selected_addons = user_data["registered_users"][str(user_id)].get("selected_automatic_addons", [])
    selected_package_names = [pkg['name'] for pkg in ADD_ON_SEQUENCE if pkg['code'] in selected_addons]

    if selected_package_names:
        text += f"\n📦 *Paket dipilih*: {', '.join(selected_package_names)}\n"
    else:
        text += "\n📦 *Paket dipilih*: _Belum ada paket yang dipilih._\n"

    total_price = 0
    for addon_code in selected_addons:
        addon_price = CUSTOM_PACKAGE_PRICES.get(addon_code, {}).get('price_bot', 0)
        total_price += addon_price
    
                                      
    xcp_8gb_price_key = f"c03be70fb3523ac2ac440966d3a5920e_{payment_method_for_xcp_8gb}" if payment_method_for_xcp_8gb == "QRIS" else XCP_8GB_PACKAGE['code']
    if payment_method_for_xcp_8gb == "PULSA":
        xcp_8gb_price_key = XCP_8GB_PULSA_PACKAGE['code']

    xcp_8gb_price = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
    total_price += xcp_8gb_price


    text += f"\n?? *Estimasi Total Harga Bot*: `Rp{total_price:,}`\n\n"


    addon_buttons = []
    for i in range(0, len(ADD_ON_SEQUENCE), 2):
        row = []
        pkg1 = ADD_ON_SEQUENCE[i]
        price1 = CUSTOM_PACKAGE_PRICES.get(pkg1['code'], {}).get('price_bot', 0)
        checkmark1 = "✅ " if pkg1['code'] in selected_addons else ""
        row.append(InlineKeyboardButton(f"{checkmark1}{pkg1['name']} (Rp{price1:,})", callback_data=f"select_auto_addon_{pkg1['code']}"))
        
        if i + 1 < len(ADD_ON_SEQUENCE):
            pkg2 = ADD_ON_SEQUENCE[i+1]
            price2 = CUSTOM_PACKAGE_PRICES.get(pkg2['code'], {}).get('price_bot', 0)
            checkmark2 = "✅ " if pkg2['code'] in selected_addons else ""
            row.append(InlineKeyboardButton(f"{checkmark2}{pkg2['name']} (Rp{price2:,})", callback_data=f"select_auto_addon_{pkg2['code']}"))
        addon_buttons.append(row)
    
    addon_buttons.append([
        InlineKeyboardButton("PILIH SEMUA 🛒", callback_data="select_all_auto_addons"),
        InlineKeyboardButton("HAPUS PILIHAN 🗑️", callback_data="clear_auto_addons_selection")
    ])

    if selected_addons:
        addon_buttons.append([InlineKeyboardButton("LANJUT ➡️", callback_data="initiate_automatic_xcs_purchase")])
    
    addon_buttons.append([InlineKeyboardButton("🔙 Kembali ke Pilihan Metode", callback_data="automatic_xcs_addon_flow")])
    
    reply_markup = InlineKeyboardMarkup(addon_buttons)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_bypass_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    text = (
        "*                  ⚠️ SYARAT BYPASS ⚠️*\n\n"
        "📌 PASTIKA WAJIB SUDAH MENCOCOKKAN NOMOR ( BUKA MENU XC 1+1GB & XUTS )\n"
        "📌 BOLEH ADA PULSA ASAL TIDAK LEBIH DARI RP.10.0000\n"
        "📌 JIKA PAKET BERHASIL DI BYPASS AKAN ADA SMS:*Transaksi Tidak Dapat Di Proses*\n"
        "📌 TIDAK ADA PAKET XTRA COMBO KECUALI FLEX\n"
        "📌 *PULSA HARUS Rp.0 SAAT BYPASS Xtra Combo Hotrod 7H*\n\n"
    )

    selected_hesdapkg_ids = user_data["registered_users"][str(user_id)].get("selected_hesdapkg_ids", [])
    selected_package_names = [pkg['name'] for pkg in HESDA_PACKAGES if pkg['id'] in selected_hesdapkg_ids]

    if selected_package_names:
        text += f"📦 *Paket yang dipilih*: {', '.join(selected_package_names)}\n\n"
    else:
        text += "📦 *Paket yang dipilih*: _Belum ada paket yang dipilih._\n\n"

    bypass_buttons = []
    for i in range(0, len(HESDA_PACKAGES), 2):
        row = []
        pkg1 = HESDA_PACKAGES[i]
                                     
        checkmark1 = "✅ " if pkg1['id'] in selected_hesdapkg_ids else ""
        row.append(InlineKeyboardButton(f"{checkmark1}{pkg1['name']} (Rp{pkg1['price_bot']:,})", callback_data=f"select_hesdapkg_{pkg1['id']}"))
        
        if i + 1 < len(HESDA_PACKAGES):
            pkg2 = HESDA_PACKAGES[i+1]
            checkmark2 = "✅ " if pkg2['id'] in selected_hesdapkg_ids else ""
            row.append(InlineKeyboardButton(f"{checkmark2}{pkg2['name']} (Rp{pkg2['price_bot']:,})", callback_data=f"select_hesdapkg_{pkg2['id']}"))
        bypass_buttons.append(row)
    
                                          
                         
    action_row = [
        InlineKeyboardButton("PILIH SEMUA 🛒", callback_data="select_all_hesdapkg"),
        InlineKeyboardButton("HAPUS PILIHAN 🗑️", callback_data="clear_hesdapkg_selection")
    ]
    bypass_buttons.append(action_row)

                                                            
    if selected_hesdapkg_ids:
        bypass_buttons.append([InlineKeyboardButton("LANJUT ➡️", callback_data="initiate_hesda_batch_purchase")])
    
                    
    bypass_buttons.append([InlineKeyboardButton("🔙 Kembali ke Menu XCS ADD ON", callback_data="xcp_addon")]) 
    reply_markup = InlineKeyboardMarkup(bypass_buttons)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_vidio_xl_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = (
        "*PAKET XTRA UNLIMITED VIDIO XL*\n"
        "solusi buat yang gak ada paket vidio di my XL harga jasa tembak 3000\n\n"
        "Silakan pilih metode pembayaran:"
    )
    keyboard = [
        [InlineKeyboardButton("BELI (PULSA)", callback_data="buy_vidio_xl_package_PULSA")],
        [InlineKeyboardButton("BELI (DANA)", callback_data="buy_vidio_xl_package_DANA")],
        [InlineKeyboardButton("BELI (QRIS)", callback_data="buy_vidio_xl_package_QRIS")],
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_iflix_xl_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = (
        "*PAKET XTRA UNLIMITED IFLIX XL*\n\n"
        "Solusi buat yang gak ada paket IFLIX di MyXL. Harga jasa tembak 3000\n\n"
        "*Silakan pilih metode pembayaran*:"
    )
    keyboard = [
        [InlineKeyboardButton("BELI (PULSA)", callback_data="buy_iflix_xl_package_PULSA")],
        [InlineKeyboardButton("BELI (DANA)", callback_data="buy_iflix_xl_package_DANA")],
        [InlineKeyboardButton("BELI (QRIS)", callback_data="buy_iflix_xl_package_QRIS")],
        [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def send_30h_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    text = (
        "* ⚠️ SYARAT PAKET BYPASS ⚠️*\n\n"
        "📌 PASTIKA WAJIB SUDAH MENCOCOKKAN NOMOR ( BUKA MENU XC 1+1GB & XUTS )\n"
        "📌 Jika berhasil, pastiin menerima SMS 'Transaksi Tidak Dapat Di Proses'. berarti nomor nya bisa.\n"
        "📌 Paket Unofficial (tanpa garansi ).\n\n"
    )

                                                           
    selected_30h_pkg_ids = user_data["registered_users"][str(user_id)].get("selected_30h_pkg_ids", [])
    selected_package_names = [pkg['name'] for pkg in THIRTY_H_PACKAGES if pkg['id'] in selected_30h_pkg_ids]

    if selected_package_names:
        text += f"📦 *Paket yang dipilih*: {', '.join(selected_package_names)}\n\n"
    else:
        text += "📦 *Paket yang dipilih*: _Belum ada paket yang dipilih._\n\n"

                                        
    thirty_h_buttons = []
    for i in range(0, len(THIRTY_H_PACKAGES), 2):
        row = []
        pkg1 = THIRTY_H_PACKAGES[i]
        checkmark1 = "✅ " if pkg1['id'] in selected_30h_pkg_ids else ""
        row.append(InlineKeyboardButton(f"{checkmark1}{pkg1['name']} (Rp{pkg1['price_bot']:,})", callback_data=f"select_30h_pkg_{pkg1['id']}"))
        
        if i + 1 < len(THIRTY_H_PACKAGES):
            pkg2 = THIRTY_H_PACKAGES[i+1]
            checkmark2 = "✅ " if pkg2['id'] in selected_30h_pkg_ids else ""
            row.append(InlineKeyboardButton(f"{checkmark2}{pkg2['name']} (Rp{pkg2['price_bot']:,})", callback_data=f"select_30h_pkg_{pkg2['id']}"))
        thirty_h_buttons.append(row)
    
                                             
    action_row = [
        InlineKeyboardButton("PILIH SEMUA 🛒", callback_data="select_all_30h_pkg"),
        InlineKeyboardButton("HAPUS PILIHAN 🗑️", callback_data="clear_30h_pkg_selection")
    ]
    thirty_h_buttons.append(action_row)

                                                            
    if selected_30h_pkg_ids:
        thirty_h_buttons.append([InlineKeyboardButton("LANJUT ➡️", callback_data="initiate_30h_batch_purchase")])
    
                    
    thirty_h_buttons.append([InlineKeyboardButton("🔙 Kembali ke Menu XCS ADD ON", callback_data="xcp_addon")]) 
    reply_markup = InlineKeyboardMarkup(thirty_h_buttons)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
    else:
        msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg.message_id)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    if user_id == ADMIN_ID:
        if data.startswith("broadcast_add_button_"):
            await admin_handle_broadcast_button_choice(update, context)
            return
        if data.startswith("broadcast_add_reply_"):
            await admin_handle_broadcast_reply_choice(update, context)
            return
        if data.startswith("admin_"):
            await admin_callback_handler(update, context)
            return    
                                                                   
        if data.startswith('hesda_api_res_'):
            await admin_callback_handler(update, context)
            return
                                                                                         
        if data.startswith('retry_single_'):
            await admin_callback_handler(update, context)                                                                  
            return
        
    if not await check_access(update, context):
        return
        
                                
    elif data == 'stop_automatic_xcs_flow':
        user_id = query.from_user.id
        await query.answer("🛑 Mengirim sinyal berhenti darurat...", show_alert=False)

        if 'automatic_xcs_flow_state' in context.user_data:
                                                      
            context.user_data['automatic_xcs_flow_state']['stop_requested'] = True

                                                          
            current_task = context.user_data['automatic_xcs_flow_state'].get('current_task')
            if current_task and not current_task.done():
                current_task.cancel()
                logging.info(f"Sinyal pembatalan dikirim ke tugas yang sedang berjalan untuk user {user_id}.")
            else:
                logging.info(f"Tombol stop ditekan user {user_id}, tapi tidak ada tugas aktif untuk dibatalkan.")
            
            try:
                await query.edit_message_text(text=" Sinyal berhenti diterima. Proses akan dihentikan secara paksa...", parse_mode="Markdown")
            except Exception:
                pass
        else:
            await query.answer("Sesi pembelian otomatis sudah tidak aktif.", show_alert=True)
        return
         
    elif data == 'skip_pending_addon':
        await query.answer("Permintaan untuk melewati paket diterima...", show_alert=False)
                                                                               
        if 'automatic_xcs_flow_state' in context.user_data:
            context.user_data['automatic_xcs_flow_state']['skip_current_wait'] = True
            simpan_data_ke_db()
        else:
            logging.warning(f"User {user_id} menekan skip_pending_addon tetapi state tidak ditemukan.")
            try:
                await query.edit_message_text("Sesi pembelian otomatis sudah tidak aktif.")
            except Exception: pass
        return
        
    elif data == 'show_login_options':                                                
        await query.answer()                        
        await show_login_options_menu(update, context)
        return

    elif data == 'qris_paid_manual_confirm':
        await query.answer("Konfirmasi diterima!", show_alert=False)
        
        active_qris_messages = context.user_data.pop('active_qris_messages', {})
        
        if active_qris_messages:
            for msg_id in active_qris_messages.values():
                if msg_id:
                    try:
                        await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                    except Exception:
                        pass

            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Terima kasih telah melakukan pembayaran.\nJika sudah membayar, tinggal menunggu paket masuk, harap bersabar..."
            )
        else:
            try:
                                                                                           
                await query.edit_message_text("Sesi pembayaran ini sudah tidak aktif atau sudah selesai.")
            except Exception:
                pass
        return                           
        return
    
    elif data == 'login_kmsp':                                  
        await query.edit_message_text(text="Masukkan nomor HP Anda untuk login LOGIN (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'kmsp'
        context.user_data['next'] = 'handle_phone_for_login'

    elif data == 'login_hesda':                                   
        await query.edit_message_text(text="Masukkan nomor HP Anda untuk login BYPAS (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'hesda'
        context.user_data['next'] = 'handle_phone_for_login'
    
    elif data == 'vidio_xl_menu':
        await send_vidio_xl_menu(update, context)
        return                                                                   

    elif data == 'iflix_xl_menu':
        await send_iflix_xl_menu(update, context)
        return

    elif data.startswith('buy_vidio_xl_package_'):
        payment_method_selected = data.replace('buy_vidio_xl_package_', '')

                                                                    
                                                                                                
        package_name_display = "XTRA UNLIMITED VIDIO XL"
        payment_method_for_api = ""                                           
        price_lookup_key = ""                                                    

        if payment_method_selected == "PULSA":
            payment_method_for_api = "BALANCE"
            package_code_for_api = "XLUNLITURBOVIDIO_PULSA"            
            price_lookup_key = "XLUNLITURBOVIDIO_PULSA"            
            package_name_display += " (PULSA)"
        elif payment_method_selected == "DANA":
            payment_method_for_api = "DANA"
            package_code_for_api = "XLUNLITURBOVIDIO_DANA"            
            price_lookup_key = "XLUNLITURBOVIDIO_DANA"            
            package_name_display += " (DANA)"
        elif payment_method_selected == "QRIS":
            payment_method_for_api = "QRIS"
            package_code_for_api = "XLUNLITURBOVIDIO_DANA"                                            
            price_lookup_key = "XLUNLITURBOVIDIO_QRIS"            
            package_name_display += " (QRIS)"
        else:
            await query.answer("Pilihan metode pembayaran tidak valid.", show_alert=True)
            return
            
        required_balance = CUSTOM_PACKAGE_PRICES.get(price_lookup_key, {}).get('price_bot', 0)
        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

        if user_balance < required_balance:
            await query.answer(f"Saldo Anda tidak cukup untuk membeli paket ini (butuh Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_balance:,}", show_alert=True)
            return

        await query.edit_message_text(
            text=f"Anda memilih: *{package_name_display}*.\nMasukkan nomor HP untuk pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="vidio_xl_menu")]]),
            parse_mode="Markdown"
        )

        context.user_data['selected_package_code'] = package_code_for_api                                                     
        context.user_data['selected_package_name_display'] = package_name_display
        context.user_data['selected_payment_method'] = payment_method_for_api
        context.user_data['selected_price_lookup_key'] = price_lookup_key
        context.user_data['selected_api_provider'] = "kmsp"
        context.user_data['next'] = 'handle_beli_single_vidio_package'
        return
       
    elif data.startswith('buy_iflix_xl_package_'):                     
        payment_method_selected = data.replace('buy_iflix_xl_package_', '')

        package_name_display = "XTRA UNLIMITED IFLIX XL"
        payment_method_for_api = "" 
        price_lookup_key = "" 

        if payment_method_selected == "PULSA":
            payment_method_for_api = "BALANCE"
            package_code_for_api = "XLUNLITURBOIFLIXXC_PULSA" 
            price_lookup_key = "XLUNLITURBOIFLIXXC_PULSA" 
            package_name_display += " (PULSA)"
        elif payment_method_selected == "DANA":
            payment_method_for_api = "DANA"
            package_code_for_api = "XLUNLITURBOIFLIXXC_EWALLET" 
            price_lookup_key = "XLUNLITURBOIFLIXXC_DANA" 
            package_name_display += " (DANA)"
        elif payment_method_selected == "QRIS":
            payment_method_for_api = "QRIS"
            package_code_for_api = "XLUNLITURBOIFLIXXC_EWALLET"                                              
            price_lookup_key = "XLUNLITURBOIFLIXXC_QRIS" 
            package_name_display += " (QRIS)"
        else:
            await query.answer("Pilihan metode pembayaran tidak valid.", show_alert=True)
            return
            
        required_balance = CUSTOM_PACKAGE_PRICES.get(price_lookup_key, {}).get('price_bot', 0)
        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

        if user_balance < required_balance:
            await query.answer(f"Saldo Anda tidak cukup untuk membeli paket ini (butuh Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_balance:,}", show_alert=True)
            return

        await query.edit_message_text(
            text=f"Anda memilih: *{package_name_display}*.\nMasukkan nomor HP untuk pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="iflix_xl_menu")]]),                        
            parse_mode="Markdown"
        )

        context.user_data['selected_package_code'] = package_code_for_api 
        context.user_data['selected_package_name_display'] = package_name_display
        context.user_data['selected_payment_method'] = payment_method_for_api
        context.user_data['selected_price_lookup_key'] = price_lookup_key
        context.user_data['selected_api_provider'] = "kmsp"
        context.user_data['next'] = 'handle_beli_single_iflix_package'                                               
        return
   
    if data == 'show_login_options':                                                
        await query.answer()                        
        await show_login_options_menu(update, context)
        return

    elif data == 'login_kmsp':                                  
        await query.edit_message_text(text="Masukkan nomor HP Anda untuk login LOGIN (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'kmsp'
        context.user_data['next'] = 'handle_phone_for_login'

    elif data == 'login_hesda':                                   
        await query.edit_message_text(text="Masukkan nomor HP Anda untuk login BYPAS (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'hesda'
        context.user_data['next'] = 'handle_phone_for_login'
    
                                
                        
    if data == 'user_reply_to_broadcast':
        await query.answer()
        msg = await context.bot.send_message(user_id, "Silakan ketik jawaban Anda dan kirim. Jawaban akan diteruskan ke Admin.")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'handle_user_broadcast_reply'
        return

                                                                                                   
                                                                                                                      
        await query.answer()

    logging.info(f"User {user_id} menekan tombol: {data}")

    if data == 'login':                         
        await query.edit_message_text(text="Masukkan nomor HP Anda (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'kmsp'
        context.user_data['next'] = 'handle_phone_for_login'
    
    elif data == 'login_hesda':                                    
        await query.edit_message_text(text="Masukkan nomor HP Anda untuk login BYPAS (contoh: `0812xxxxxxxx` atau `62812xxxxxxxx`):", parse_mode="Markdown")
        context.user_data['current_login_provider'] = 'hesda'
        context.user_data['next'] = 'handle_phone_for_login'

    elif data == 'akun_saya':                          
        await akun_saya_command_handler(update, context)
        return

    elif data == 'tembak_paket':
       
        harga_text = (
            "> " + escape_markdown("✨ HARGA DOR XC 1+1GB & XUTS: 5.200", version=2) + "\n" +
            "> " + escape_markdown("💳 SIAPIN SALDO BUAT BAYAR XC 1+1GB Rp.12.500 ️", version=2) + "\n" +
            "> " + escape_markdown("💵 TOTAL BAYAR XUTS Rp.17.700 ✅", version=2) + "\n\n" + 
            "> " + escape_markdown("🌟 HARGA DOR XUTP: 5.200", version=2) + "\n" +
            "> " + escape_markdown("💳 SIAPIN SALDO BUAT BAYAR XCP 8GB Rp.25.000", version=2) + "\n" +
            "> " + escape_markdown("💵  TOTAL BAYAR XUTP Rp.30.200 ✅", version=2) + "\n\n" +
            "> " + escape_markdown("⚡ HARGA DOR XCS ADD ON: 7.400 ( HARGA FULL ADD ON )", version=2) + "\n" +
            "> " + escape_markdown("💳 SIAPIN SALDO BUAT BAYAR XCP 8GB Rp.25.000", version=2) + "\n" +
            "> " + escape_markdown("💵  TOTAL XCS ADD ON Rp32.400 ✅", version=2) + "\n\n" +
            
            "> " + escape_markdown("NOTE. harga XCS di atas adalah harga  FULL ADD ON harga nya bisa kurang jika tidak membeli semua ADD ON harga per ADD ON 200", version=2)
        )
        
        message_text = "🔥 *DAFTAR HARGA PAKET* 🔥\n\n" + harga_text
        tembak_buttons = [
            [InlineKeyboardButton("✨ XUTS", callback_data="menu_uts_nested")],
            [InlineKeyboardButton("🌟 XUTP", callback_data="xutp_menu")],
            [InlineKeyboardButton("⚡ XCS ADD ON", callback_data="xcp_addon")],
            [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(tembak_buttons)
        await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode="MarkdownV2")

    elif data == 'xutp_menu':
        await send_xutp_method_selection_menu(update, context)
        return

    elif data.startswith('xutp_method_'):
        await query.answer()
        payment_method_for_xutp = data.replace('xutp_method_', '').upper()
        
        if payment_method_for_xutp == "PULSA":
            context.user_data['xutp_purchase_payment_method'] = "BALANCE" 
            display_method_name = "PULSA" 
        else:
            context.user_data['xutp_purchase_payment_method'] = payment_method_for_xutp
            display_method_name = payment_method_for_xutp 

        await query.edit_message_text(
            text=f"Anda memilih mode XUTP dengan pembayaran *{display_method_name}*.\nMasukkan nomor HP untuk memproses pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="xutp_menu")]]),
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'handle_automatic_xutp_phone_input'
        return

    elif data == 'menu_uts_nested':
        await send_uts_menu(update, context)
    
    elif data == 'menu_bypass_nested':                                                     
        await send_bypass_menu(update, context)

    elif data == 'xcp_addon_dana':                                              
        await send_xcp_addon_dana_menu(update, context)
   
    elif data == 'automatic_purchase_flow':                    
        await query.answer()
        message_text = "Silakan pilih metode pembayaran untuk pembelian paket otomatis:"
        keyboard = [
            [InlineKeyboardButton("DANA", callback_data="automatic_method_dana")],
            [InlineKeyboardButton("PULSA", callback_data="automatic_method_pulsa")],
            [InlineKeyboardButton("QRIS", callback_data="automatic_method_qris")],
            [InlineKeyboardButton("🔙 Kembali ke Menu XC 1+1GB & XUTS", callback_data="menu_uts_nested")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        return

    elif data.startswith('automatic_method_'):
        await query.answer()
        payment_method_for_auto = data.replace('automatic_method_', '').upper()
        
        if payment_method_for_auto == "PULSA":
            context.user_data['automatic_purchase_payment_method'] = "BALANCE"
            display_method_name = "PULSA"
        else:
            context.user_data['automatic_purchase_payment_method'] = payment_method_for_auto
            display_method_name = payment_method_for_auto

        await query.edit_message_text(
            text=f"Anda memilih mode Otomatis dengan pembayaran *{display_method_name}*.\nMasukkan nomor HP untuk memproses pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="automatic_purchase_flow")]]),
            parse_mode="Markdown"
        )
        context.user_data['next'] = 'handle_automatic_purchase_phone_input'
        return

    elif data == 'manual_uts_selection_menu': 
        await query.answer()
        await send_manual_uts_selection_menu(update, context)
        return

    elif data == 'cek_saldo':
        balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)
        await query.answer(f"💰 Saldo Anda saat ini: Rp{balance:,}", show_alert=True)
        return

    elif data == 'top_up_saldo':
        await query.edit_message_text(text=f"Masukkan nominal top up yang diinginkan (minimal Rp{MIN_TOP_UP_AMOUNT:,}, contoh: `10000`):", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Kembali", callback_data="back_to_menu")]]),
                                      parse_mode="Markdown")
        context.user_data['next'] = 'handle_top_up_amount'
        return

    elif data == 'cek_kuota':
        await query.edit_message_text(text="Masukkan nomor HP XL/Axis yang ingin dicek kuotanya (contoh: `0878...`):", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Kembali", callback_data="back_to_menu")]]), 
                                      parse_mode="Markdown")
        context.user_data['next'] = 'handle_cek_kuota_baru_input'
        return

    elif data == 'tutorial_beli':
        keyboard = [
            [InlineKeyboardButton("❗Syarat Pembelian❗", callback_data='syarat_pembelian')],
            [InlineKeyboardButton("📖 Tutorial Pembelian XCS ADD-ONS", callback_data='tutorial_xcs_addons')],
            [InlineKeyboardButton("📖 Tutorial Pembelian XUTS", callback_data='tutorial_uts')],
            [InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Pilih tutorial yang ingin Anda lihat:", parse_mode="Markdown", reply_markup=reply_markup)

    elif data == 'syarat_pembelian':
        syarat_pembelian_text = """
❗ *Syarat Pembelian* ❗

1. Sudah Login OTP
2. Tidak ada paket Xtra Combo varian apapun kecuali XC Flex di `*808#` > INFO > Info Kartu XL-Ku > Stop Langganan. Jika ada Xtra Combo silahkan di stop
3. Kartu tidak boleh dalam masa tenggang
4. Saldo buat bayar 
    - Rp25.000 Untuk Add on XCS 
    - Rp12.500 Untuk XUTS 
5. Pastikan saldo bot cukup
"""
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Tutorial Beli", callback_data='tutorial_beli')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(syarat_pembelian_text, parse_mode="Markdown", reply_markup=reply_markup)

    elif data == 'tutorial_xcs_addons':
        tutorial_xcs_addons_text = """
📖 *Tutorial Pembelian XCS ADD-ONS* 📖

1. Pilih MENU TEMBAK PAKET
2. pilih XCS ADD ON
3. Pilih mode OTOMATIS lalu pilih metode bayar nya ( saran make QRIS)
4. Setelah itu pilih add on yang mau di beli, jika sudah selesai memilih add on nya klik lanjut 
5. Masukin nomor nya setelah itu bot akan memproses pembelian secara otomatis 
6. Kalo sudah selesai nanti akan ada gambar QRIS,link pembayaran dana (sesuai metode pembayaran yang di pilih)
7. Siapkan saldo ewallet,mbanking atau pulsa untuk bayar *Rp25.000*
8. TINGGAL MENUNGGU ADD ON MASUK 15 MENIT SAMPAI 2 JAM PASTIKAN TIDAK ADA TRANSAKSI

❕ *Catatan*
1. Kelalaian/kesalahan pengguna tidak ada refund saldo bot!
2. Add on bersifat hoki hokian (bisa masuk bisa tidak)
3. Saldo bot tidak bisa dicairkan kembali
4. Paket Unofficial, tidak ada garansi.!
5. Segala Konsekwensinya Di tanggung User
"""
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Tutorial Beli", callback_data='tutorial_beli')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tutorial_xcs_addons_text, parse_mode="Markdown", reply_markup=reply_markup)

    elif data == 'tutorial_uts':
        tutorial_uts_text = """
📖 *Tutorial Pembelian XUTS*📖 

1. Pilih menu tembak paket pilih menu XUTS 
2. Pilih menu OTOMATIS 
3. Pilih metode pembayaran nya bisa QRIS,PULSA,DANA ( saran menggunakan QRIS )
4. Klik lanjut masukan nomor nya lalu biarkan proses nya berlangsung 
5. Kalo sudah selesai nanti akan ada gambar QRIS,link pembayaran dana (sesuai metode pembayaran yang di pilih)
6. Siapkan saldo ewallet,mbanking atau pulsa untuk bayar *Rp12.500*
7. jika sudah membayar tinggal menunggu paket masuk
8. Biarkan Kartu Nya Jangan Ada Transaksi

❕ *Catatan*
1. Kelalaian/kesalahan pengguna tidak ada refund saldo bot!
2. Add on bersifat hoki hokian (bisa masuk bisa tidak)
3. Saldo bot tidak bisa dicairkan kembali
4. Paket Unofficial, tidak ada garansi.!
5. Segala Konsekwensinya Di tanggung User
"""
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Tutorial Beli", callback_data='tutorial_beli')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(tutorial_uts_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif data == 'back_to_menu':
        await send_main_menu(update, context)
        simpan_data_ke_db()
        return
    
    elif data == 'xcp_addon':                                                      
        await send_xcp_addon_menu(update, context)

    elif data == 'manual_xcs_addon_selection_menu':                                 
        await send_manual_xcs_addon_selection_menu(update, context)

    elif data == 'automatic_xcs_addon_flow':                                                       
        await send_automatic_xcs_addon_method_selection_menu(update, context)

    elif data.startswith('auto_xcs_method_'):                                                          
        payment_method_for_xcp_8gb = data.replace('auto_xcs_method_', '').upper()
        context.user_data['automatic_xcs_payment_method'] = payment_method_for_xcp_8gb
        context.user_data['selected_automatic_addons'] = []                                           
        await send_automatic_xcs_addon_package_selection_menu(update, context)

    elif data.startswith('select_auto_addon_'):                                                                        
        addon_code = data.replace('select_auto_addon_', '')
        user_selected_addons = user_data["registered_users"][str(user_id)].setdefault("selected_automatic_addons", [])
        
        if addon_code in user_selected_addons:
            user_selected_addons.remove(addon_code)
            await query.answer(f"Paket dihapus dari pilihan.")
        else:
            user_selected_addons.append(addon_code)
            await query.answer(f"Paket ditambahkan ke pilihan.")
        
        simpan_data_ke_db()
        await send_automatic_xcs_addon_package_selection_menu(update, context)                  
    
    elif data == 'select_all_auto_addons':                      
        all_addon_codes = [pkg['code'] for pkg in ADD_ON_SEQUENCE]
        user_data["registered_users"][str(user_id)]["selected_automatic_addons"] = all_addon_codes
        simpan_data_ke_db()
        await query.answer("Semua paket ADD ON telah dipilih.")
        await send_automatic_xcs_addon_package_selection_menu(update, context)

    elif data == 'clear_auto_addons_selection':                        
        user_data["registered_users"][str(user_id)]["selected_automatic_addons"] = []
        simpan_data_ke_db()
        await query.answer("Pilihan paket ADD ON telah dihapus.")
        await send_automatic_xcs_addon_package_selection_menu(update, context)

    elif data == 'initiate_automatic_xcs_purchase':                                      
        selected_addons = user_data["registered_users"][str(user_id)].get("selected_automatic_addons", [])
        if not selected_addons:
            await query.answer("Anda belum memilih paket ADD ON apapun.", show_alert=True)
            return

        payment_method_for_xcp_8gb = context.user_data.get('automatic_xcs_payment_method')

        total_price_addons = 0
        for addon_code in selected_addons:
                                                                      
            price_info = CUSTOM_PACKAGE_PRICES.get(addon_code)
            if isinstance(price_info, dict):
                total_price_addons += price_info.get('price_bot', 0)
            else:                                                                                                    
                total_price_addons += price_info if isinstance(price_info, (int, float)) else 0
        
                                          
        xcp_8gb_price_key = f"c03be70fb3523ac2ac440966d3a5920e_{payment_method_for_xcp_8gb}" if payment_method_for_xcp_8gb == "QRIS" else XCP_8GB_PACKAGE['code']
        if payment_method_for_xcp_8gb == "PULSA":
            xcp_8gb_price_key = XCP_8GB_PULSA_PACKAGE['code']                                                       

        xcp_8gb_price = CUSTOM_PACKAGE_PRICES.get(xcp_8gb_price_key, {}).get('price_bot', 0)
        
        total_required_balance = total_price_addons + xcp_8gb_price

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        if user_current_balance < total_required_balance:
            await query.answer(f"Saldo Anda tidak cukup. Saldo Anda Rp{user_current_balance:,}, dibutuhkan Rp{total_required_balance:,}", show_alert=True)
            return
        
                                                       
        if total_required_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] -= total_required_balance
            simpan_data_ke_db()
            await query.answer(f"Saldo Anda terpotong: Rp{total_required_balance:,}. Silakan masukkan nomor HP.", show_alert=False) 
            logging.info(f"Saldo user {user_id} dipotong sebesar {total_required_balance} untuk batch XCS ADD ON otomatis.")
        else:
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await query.answer(f"Saldo minimal Rp{MIN_BALANCE_FOR_PURCHASE:,} dibutuhkan untuk transaksi.", show_alert=True)
                return

        context.user_data['total_automatic_xcs_price'] = total_required_balance
        context.user_data['automatic_xcs_flow_state'] = {                                         
            'phone': None,
            'access_token': None,
            'payment_method_xcp_8gb': payment_method_for_xcp_8gb,
            'addons_to_process': selected_addons,
            'current_addon_index': 0,
            'xcp_8gb_completed': False,
            'overall_status_message_id': None,
            'addon_retry_count': 0,
            'has_waited_for_pending_once': False,  
            'addon_long_delay_done': False, 
            'addon_results': {},            
            'addon_pass_retry_count': {},   
        }
        user_data["registered_users"][str(user_id)]["selected_automatic_addons"] = []                        
        simpan_data_ke_db() 
        
        await query.edit_message_text(
            text="Masukkan nomor HP untuk memproses pembelian XCS ADD ON Otomatis:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="automatic_xcs_addon_flow")]])
        )
        context.user_data['next'] = 'handle_automatic_xcs_addon_phone_input'
        
    elif data == 'menu_30h_nested':   
        await send_30h_menu(update, context)  

    elif data.startswith("select_30h_pkg_"): 
        selected_package_id = data.replace("select_30h_pkg_", "")
        user_selected_packages = user_data["registered_users"][str(user_id)].setdefault("selected_30h_pkg_ids", [])                   
        
        if selected_package_id in user_selected_packages:
            user_selected_packages.remove(selected_package_id)
            await query.answer(f"Paket dihapus dari pilihan.")
        else:
            user_selected_packages.append(selected_package_id)
            await query.answer(f"Paket ditambahkan ke pilihan.")
        
        simpan_data_ke_db()
        await send_30h_menu(update, context)
    
    elif data == "initiate_30h_batch_purchase": 
        selected_30h_pkg_ids = user_data["registered_users"][str(user_id)].get("selected_30h_pkg_ids", [])
        if not selected_30h_pkg_ids:
            await query.answer("Anda belum memilih paket 30H apapun.", show_alert=True)
            return

        total_required_balance = 0
        for pkg_id in selected_30h_pkg_ids:
            pkg_info = next((p for p in THIRTY_H_PACKAGES if p["id"] == pkg_id), None)
            if pkg_info:
                total_required_balance += pkg_info['price_bot']

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        if user_current_balance < total_required_balance:
            await query.answer(f"Saldo tidak cukup. Saldo Anda Rp{user_current_balance:,}, dibutuhkan Rp{total_required_balance:,}", show_alert=True)
            return
        
        if total_required_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] -= total_required_balance
            simpan_data_ke_db()
            await query.answer(f"Saldo Anda terpotong: Rp{total_required_balance:,}. Silakan masukkan nomor HP.", show_alert=False) 
            logging.info(f"Saldo user {user_id} dipotong sebesar {total_required_balance} untuk batch 30H.")
        else:
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await query.answer(f"Saldo minimal Rp{MIN_BALANCE_FOR_PURCHASE:,} dibutuhkan untuk transaksi.", show_alert=True)
                return

        context.user_data['total_30h_batch_price'] = total_required_balance
        
        await query.edit_message_text(
            text="Masukkan nomor HP untuk memproses paket 30H yang dipilih:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_30h_nested")]])
        )
        context.user_data['next'] = 'handle_phone_for_30h_batch_purchase'
        context.user_data['current_30h_batch_results'] = []                                

    elif data == "clear_30h_pkg_selection": 
        user_data["registered_users"][str(user_id)]["selected_30h_pkg_ids"] = []
        simpan_data_ke_db()
        await query.answer("Pilihan paket 30H telah dihapus.")
        await send_30h_menu(update, context)
        
    elif data == "select_all_30h_pkg": 
        all_package_ids = [pkg['id'] for pkg in THIRTY_H_PACKAGES]
        user_data["registered_users"][str(user_id)]["selected_30h_pkg_ids"] = all_package_ids
        
        simpan_data_ke_db()
        await query.answer("Semua paket 30H telah dipilih.")
        await send_30h_menu(update, context)     
   
   
    elif data.startswith("xcp_"):
        selected_package_raw = data.replace("xcp_", "")                                                                                               

                                                              
        if selected_package_raw.endswith("_QRIS"):
            selected_package_code = selected_package_raw.replace("_QRIS", "")
            payment_method_for_api = "QRIS"
                                              
            package_name_display = XCP_8GB_PACKAGE['name'] + " QRIS"
        else:
            selected_package_code = selected_package_raw
                                                                     
            if selected_package_code == XCP_8GB_PULSA_PACKAGE['code']:
                payment_method_for_api = "BALANCE"
                package_name_display = XCP_8GB_PULSA_PACKAGE['name']
            else:                                                                    
                payment_method_for_api = "DANA"
                package_info = next((p for p in ADD_ON_SEQUENCE if p["code"] == selected_package_code), None)
                if package_info:
                    package_name_display = package_info["name"]
                elif selected_package_code == XCP_8GB_PACKAGE['code']:
                    package_name_display = XCP_8GB_PACKAGE['name']
                else:
                    package_name_display = selected_package_code           


        required_balance = CUSTOM_PACKAGE_PRICES.get(selected_package_raw, {}).get('price_bot', 0)
        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

        if user_balance < required_balance:
            await query.answer(f"Saldo Anda tidak cukup (butuh Rp{required_balance:,})", show_alert=True)
            return
        
                                              
        if selected_package_code == XCP_8GB_PACKAGE['code']:                             
            back_callback = "xcp_addon"
        else:                                   
            back_callback = "xcp_addon_dana"
            
        await query.edit_message_text(
            text=f"Anda memilih: *{package_name_display}*.\nMasukkan nomor HP untuk pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=back_callback)]]),
            parse_mode="Markdown"
        )
        
        context.user_data['selected_package_code'] = selected_package_code
        context.user_data['selected_payment_method'] = payment_method_for_api
        context.user_data['selected_api_provider'] = "kmsp"
        context.user_data['next'] = 'handle_beli_xcp'

    elif data.startswith("select_hesdapkg_"):
        selected_package_id = data.replace("select_hesdapkg_", "")
        user_selected_packages = user_data["registered_users"][str(user_id)]["selected_hesdapkg_ids"]
        
        if selected_package_id in user_selected_packages:
            user_selected_packages.remove(selected_package_id)
            await query.answer(f"Paket dihapus dari pilihan.")
        else:
            user_selected_packages.append(selected_package_id)
            await query.answer(f"Paket ditambahkan ke pilihan.")
        
        simpan_data_ke_db()
        await send_bypass_menu(update, context)
    
    elif data == "initiate_hesda_batch_purchase":
        selected_hesdapkg_ids = user_data["registered_users"][str(user_id)].get("selected_hesdapkg_ids", [])
        if not selected_hesdapkg_ids:
            await query.answer("Anda belum memilih paket apapun.", show_alert=True)
            return

        total_required_balance = 0
        for pkg_id in selected_hesdapkg_ids:
            pkg_info = next((p for p in HESDA_PACKAGES if p["id"] == pkg_id), None)
            if pkg_info:
                total_required_balance += pkg_info['price_bot']

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        if user_current_balance < total_required_balance:
            await query.answer(f"Saldo tidak cukup. Saldo Anda Rp{user_current_balance:,}, dibutuhkan Rp{total_required_balance:,}", show_alert=True)
            return
        
                                                               
        if total_required_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] -= total_required_balance
            simpan_data_ke_db()
            await query.answer(f"Saldo Anda terpotong: Rp{total_required_balance:,}. Silakan masukkan nomor HP.", show_alert=False)                    
            logging.info(f"Saldo user {user_id} dipotong sebesar {total_required_balance} untuk batch Hesda.")
        else:
                                                                     
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await query.answer(f"Saldo minimal Rp{MIN_BALANCE_FOR_PURCHASE:,} dibutuhkan untuk transaksi.", show_alert=True)
                return

                                                                                      
        context.user_data['total_hesdapkg_batch_price'] = total_required_balance
        
                                                        
        await query.edit_message_text(
            text="Masukkan nomor HP untuk memproses paket BYPAS yang dipilih:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_bypass_nested")]])
        )
        context.user_data['next'] = 'handle_phone_for_hesda_batch_purchase'
        context.user_data['current_hesda_batch_results'] = []                                

    elif data == "clear_hesdapkg_selection":
        user_data["registered_users"][str(user_id)]["selected_hesdapkg_ids"] = []
        simpan_data_ke_db()
        await query.answer("Pilihan paket BYPAS telah dihapus.")
        await send_bypass_menu(update, context)
        
    elif data == "select_all_hesdapkg":
                                                            
        all_package_ids = [pkg['id'] for pkg in HESDA_PACKAGES]
        
                                                                      
        user_data["registered_users"][str(user_id)]["selected_hesdapkg_ids"] = all_package_ids
        
        simpan_data_ke_db()
        await query.answer("Semua paket bypass telah dipilih.")
        
                                                               
        await send_bypass_menu(update, context)     

    elif data.startswith("ganti_"):
        nomor_baru = data.replace("ganti_", "")
        if nomor_baru in user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}):
            user_data["registered_users"][str(user_id)]["current_phone"] = nomor_baru
            simpan_data_ke_db()
            logging.info(f"User {user_id} mengganti akun aktif ke {nomor_baru}")
            try:
                await query.edit_message_text(f"✅ Nomor aktif diubah ke `{nomor_baru}`", parse_mode="Markdown")
            except Exception as e:
                logging.warning(f"Gagal mengedit pesan setelah ganti akun: {e}. Mengirim pesan baru.")
                msg = await context.bot.send_message(user_id, f"✅ Nomor aktif diubah ke `{nomor_baru}`", parse_mode="Markdown")
                bot_messages.setdefault(user_id, []).append(msg.message_id)
            
            await akun_saya_command_handler(update, context)
        else:
            msg = await context.bot.send_message(user_id, "❌ Nomor tidak ditemukan di akunmu.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
        return

    elif data == 'resend_otp':
        phone = user_data.get("registered_users", {}).get(str(user_id), {}).get("current_phone")
        current_provider = context.user_data.get('current_login_provider')

        if not phone:
            msg = await context.bot.send_message(user_id, "Nomor HP tidak ditemukan. Silakan coba Login ulang.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            return
        
        login_counter[user_id] = 0
        if current_provider == 'kmsp':
            await request_otp_and_prompt_kmsp(update, context, phone)
        elif current_provider == 'hesda':
            await request_otp_and_prompt_hesda(update, context, phone)
    
    elif data.startswith("buy_uts_"):
        package_type = data.replace("buy_uts_", "")
        
        selected_package_code = ""
        package_name_display = ""
        payment_method_for_api = ""

        if package_type == "pulsa_gandengan":
            selected_package_code = "XLUNLITURBOSUPERXC_PULSA"
            package_name_display = "XUTS"
            payment_method_for_api = "BALANCE"                           
        elif package_type == "1gb":
            selected_package_code = "XL_XC1PLUS1DISC_EWALLET"
            package_name_display = "XC 1+1GB DANA"
            payment_method_for_api = "DANA"                           
        elif package_type == "1gb_pulsa": 
            selected_package_code = "XL_XC1PLUS1DISC_PULSA" 
            package_name_display = "XC 1+1GB PULSA" 
            payment_method_for_api = "BALANCE"                           
        elif package_type == "1gb_qris":                                
            selected_package_code = "XL_XC1PLUS1DISC_EWALLET"                            
            package_name_display = "XC 1+1GB QRIS"
            payment_method_for_api = "QRIS"                             
        else:
            await query.answer("Pilihan tidak valid.", show_alert=True)
            return

                                                              
        price_lookup_key = selected_package_code
        if package_type == "1gb_qris":
             price_lookup_key = "XL_XC1PLUS1DISC_QRIS"                            

        required_balance = CUSTOM_PACKAGE_PRICES.get(price_lookup_key, {}).get('price_bot', 0)
        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

        if user_balance < required_balance:
            await query.answer(f"Saldo Anda tidak cukup (butuh Rp{required_balance:,})", show_alert=True)
            return
        
                                           
        await query.edit_message_text(
            text=f"Anda memilih: *{package_name_display}*.\nMasukkan nomor HP untuk pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_uts_nested")]]),
            parse_mode="Markdown"
        )

        context.user_data['selected_package_code'] = selected_package_code
        context.user_data['selected_payment_method'] = payment_method_for_api
        context.user_data['selected_api_provider'] = "kmsp"
        context.user_data['next'] = 'handle_beli_uts_package'

    elif data == 'buy_all_addons':
        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)
        if user_balance < MIN_BALANCE_FOR_PURCHASE:
            await query.answer("Saldo tidak cukup", show_alert=True)
            text = (f"❌ Saldo Anda tidak cukup untuk memulai pembelian batch.\n"
                    f"Saldo Anda: *Rp{user_balance:,}*\n"
                    f"Saldo Minimal: *Rp{MIN_TOP_UP_AMOUNT:,}*\n"
                    f"Silakan isi saldo terlebih dahulu.")
            
            keyboard = [[InlineKeyboardButton("🏠 Kembali ke Menu Paket XCS", callback_data="xcp_addon_dana")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            msg = await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            return

        context.user_data['addon_batch_current'] = 1
        context.user_data['selected_api_provider'] = "kmsp"
        msg = await context.bot.send_message(user_id, "Anda memilih untuk membeli *SEMUA ADD ON* secara bertahap.\nMasukkan nomor HP yang akan diisi paket:", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        context.user_data['next'] = 'handle_all_addons_phone_input'
        return
    
    elif data == 'stop_batch_purchase':
        await query.answer("Mengirim sinyal berhenti...")
        context.user_data['stop_batch_purchase'] = True
        logging.info(f"User {user_id} meminta untuk menghentikan batch purchase.")
        await context.bot.edit_message_text(chat_id=user_id, message_id=query.message.message_id, text="⏳ Proses penghentian diminta, harap tunggu...", reply_markup=None)
        return

    elif data.startswith('continue_addon_batch_'):
        next_batch_num = int(data.split('_')[-1])
        context.user_data['addon_batch_current'] = next_batch_num
        asyncio.create_task(process_addon_batch(update, context))
        return

    elif data == 'show_custom_packages':
        await show_custom_packages_for_user(update, context)

    elif data.startswith("buy_custom_package_"):
        package_code = data.replace("buy_custom_package_", "")
        package_details = user_data["custom_packages"].get(package_code)
        
        if not package_details:
            await query.answer("Paket kustom tidak dikenali.", show_alert=True)
            return
        
        package_name = package_details['name']
        package_price = package_details['price']

        user_balance = user_data.get("registered_users", {}).get(str(user_id), {}).get("balance", 0)

        if user_balance < package_price:
            await query.answer(f"Saldo Anda tidak cukup (butuh Rp{package_price:,})", show_alert=True)
            return
        
                                           
        await query.edit_message_text(
            text=f"Anda memilih: *{package_name}*.\nMasukkan nomor HP untuk pembelian:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="show_custom_packages")]]),
            parse_mode="Markdown"
        )
        
        context.user_data['selected_custom_package_code'] = package_code
        context.user_data['selected_custom_package_name'] = package_name
        context.user_data['selected_custom_package_price'] = package_price
        context.user_data['selected_api_provider'] = "kmsp"
        context.user_data['next'] = 'handle_buy_custom_package_phone_input'
    

    elif data.startswith("view_custom_package_"):
        await show_custom_package_details(update, context)
        return
    elif data.startswith("buy_custom_"):
        await handle_custom_package_payment_selection(update, context)
        return

    
    elif data.startswith("retry_single_"):
        pass

    elif data == 'hapus_akun_menu':
        await hapus_akun_menu(update, context)
        return
    elif data.startswith('pilih_hapus_'):
        phone_to_delete = data.replace('pilih_hapus_', '')
        await konfirmasi_hapus_akun(update, context, phone_to_delete)
        return
    elif data.startswith('konfirmasi_hapus_'):
        phone_to_delete = data.replace('konfirmasi_hapus_', '')
        await eksekusi_hapus_akun(update, context, phone_to_delete)
        return
    elif data == 'batal_hapus_akun':
        await query.answer("Penghapusan dibatalkan.")
        await akun_saya_command_handler(update, context)                            
        return

async def request_otp_and_prompt_kmsp(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    user_id = update.effective_user.id
    try:
        url = f"https://golang-openapi-reqotp-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&phone={phone}&method=OTP"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        result = response.json()
        auth_id = result.get('data', {}).get('auth_id')
        
        logging.info(f"Response OTP KMSP request for {phone}: {result}")

        if not auth_id:
            api_error_message = result.get("message", "Auth ID tidak ditemukan di respons API.")                  
            raise ValueError(api_error_message)
        
        user_data["registered_users"].setdefault(str(user_id), {})
        user_data["registered_users"][str(user_id)].setdefault('accounts', {})
                                                           
        user_data["registered_users"][str(user_id)]['accounts'].setdefault(phone, {}).setdefault('kmsp', {})['auth_id'] = auth_id
        user_data["registered_users"][str(user_id)]['current_phone'] = phone
        simpan_data_ke_db()
        
        msg = await context.bot.send_message(user_id, f"📲 Kode OTP LOGIN telah dikirim ke *{phone}*\nSilakan masukkan kode OTP-nya.", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)

        keyboard = [[InlineKeyboardButton("🔄 Kirim Ulang OTP", callback_data='resend_otp')],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg2 = await context.bot.send_message(user_id, "Jika belum menerima OTP, tekan tombol di bawah atau masukkan kode OTP Anda:", parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg2.message_id)

        context.user_data['next'] = 'handle_login_otp_input'
        login_counter[user_id] = 0
        context.user_data['current_login_provider'] = 'kmsp'
        
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.json().get("message", "unknown error") if http_err.response.content else "no response content"
        logging.error(f"HTTP error saat request OTP KMSP untuk {phone}: {http_err}. Respon: {http_err.response.text}. Detail: {error_detail}")
        msg = await context.bot.send_message(user_id, f"Terjadi kesalahan saat request OTP: {error_detail}. Mohon coba lagi nanti.")                        
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error saat request OTP KMSP untuk {phone}: {e}")
        msg = await context.bot.send_message(user_id, f"Terjadi kesalahan jaringan saat request OTP. Mohon coba lagi nanti.")                        
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except json.JSONDecodeError:
        logging.error(f"Gagal mengurai JSON dari respon request OTP KMSP. Respon: {response.text}")
        msg = await context.bot.send_message(user_id, "Terjadi kesalahan saat memproses data OTP (JSON tidak valid).")                        
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except ValueError as e:
        logging.error(f"Kesalahan data OTP KMSP: {e}")
        msg = await context.bot.send_message(user_id, f"Gagal memproses request OTP: {e}")                        
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except Exception as e:
        logging.error(f"Kesalahan tak terduga saat request OTP KMSP: {e}", exc_info=True)
        msg = await context.bot.send_message(user_id, "Terjadi kesalahan tak terduga saat request OTP. Silakan laporkan ini kepada admin.")                        
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)

async def request_otp_and_prompt_hesda(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    user_id = update.effective_user.id
    try:
        url = "https://api.hesda-store.com/v2/get_otp"
        headers = get_hesda_auth_headers()
        if not headers:
            msg = await context.bot.send_message(user_id, "Informasi otentikasi tidak lengkap. Mohon hubungi admin.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            await send_main_menu(update, context)
            return

        payload = {
            "hesdastore": HESDA_API_KEY,
            "no_hp": phone,
            "metode": "OTP"
        }
        
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

                                       
        processed_result_data = None
        if isinstance(result, list) and len(result) > 0:
                                                                                      
            if isinstance(result[0], dict):
                processed_result_data = result[0]
            else:
                raise ValueError("Respons API Hesda adalah list, tetapi elemen pertama bukan dictionary.")
        elif isinstance(result, dict):
                                                              
            processed_result_data = result
        else:
            raise ValueError("Respons API Hesda tidak dalam format yang diharapkan (bukan dictionary atau list of dictionary).")

        auth_id = processed_result_data.get('data', {}).get('auth_id')
                                     
        
        logging.info(f"Response OTP Hesda request for {phone}: {result}")

        if not auth_id:
            api_error_message = processed_result_data.get("message", "Auth ID tidak ditemukan di respons.")                  
            raise ValueError(api_error_message)
        
        user_data["registered_users"].setdefault(str(user_id), {})
        user_data["registered_users"][str(user_id)].setdefault('accounts', {})
        user_data["registered_users"][str(user_id)]['accounts'].setdefault(phone, {}).setdefault('hesda', {})['auth_id'] = auth_id
        user_data["registered_users"][str(user_id)]['current_phone'] = phone
        simpan_data_ke_db()
        
        msg = await context.bot.send_message(user_id, f"📲 Kode OTP BYPAS telah dikirim ke *{phone}*\nSilakan masukkan kode OTP-nya.", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)

        keyboard = [[InlineKeyboardButton("🔄 Kirim Ulang OTP", callback_data='resend_otp')],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg2 = await context.bot.send_message(user_id, "Jika belum menerima OTP, tekan tombol di bawah atau masukkan kode OTP Anda:", parse_mode="Markdown", reply_markup=reply_markup)
        bot_messages.setdefault(user_id, []).append(msg2.message_id)

        context.user_data['next'] = 'handle_login_otp_input'
        login_counter[user_id] = 0
        context.user_data['current_login_provider'] = 'hesda'
        
    except requests.exceptions.HTTPError as http_err:
        error_detail = "unknown error"
        try:
            if http_err.response and http_err.response.content:
                error_detail = http_err.response.json().get("message", "no response message")
        except json.JSONDecodeError:
            error_detail = f"HTTP Error {http_err.response.status_code} with non-JSON response."
        
        logging.error(f"HTTP error saat request OTP Hesda untuk {phone}: {http_err}. Respon: {http_err.response.text}. Detail: {error_detail}")
        msg = await context.bot.send_message(user_id, f"Terjadi kesalahan saat request OTP: {error_detail}. Mohon coba lagi nanti.", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error saat request OTP Hesda untuk {phone}: {e}")
        msg = await context.bot.send_message(user_id, f"Terjadi kesalahan jaringan saat request OTP. Mohon coba lagi nanti.", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except json.JSONDecodeError:
        logging.error(f"Gagal mengurai JSON dari respon request OTP Hesda. Respon: {response.text}")
        msg = await context.bot.send_message(user_id, "Terjadi kesalahan saat memproses data OTP (JSON tidak valid).", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except ValueError as e:
        logging.error(f"Kesalahan data OTP Hesda: {e}")
        msg = await context.bot.send_message(user_id, f"Gagal memproses request OTP: {e}", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)
    except Exception as e:
        logging.error(f"Kesalahan tak terduga saat request OTP Hesda: {e}", exc_info=True)
        msg = await context.bot.send_message(user_id, "Terjadi kesalahan tak terduga saat request OTP. Silakan laporkan ini kepada admin.", parse_mode="Markdown")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await send_main_menu(update, context)

def get_hesda_auth_headers():
    if not HESDA_USERNAME or not HESDA_PASSWORD:
        logging.error("HESDA_USERNAME atau HESDA_PASSWORD tidak diatur. Tidak dapat membuat header otentikasi Hesda.")
        return None
    auth_string = f"{HESDA_USERNAME}:{HESDA_PASSWORD}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    return {"Authorization": f"Basic {encoded_auth}"}

async def schedule_top_up_expiration(context: ContextTypes.DEFAULT_TYPE, user_id: int, unique_amount: int):
    """Tunggu 5 menit, lalu cek apakah top up masih pending. Jika ya, batalkan."""
    try:
        await asyncio.sleep(300)                           

        user_details = user_data.get("registered_users", {}).get(str(user_id), {})
        
                                                                                                      
                                                                                            
        if user_details and user_details.get("pending_top_up", {}).get("unique_amount") == unique_amount:
            
            pending_info = user_details["pending_top_up"]                     
            user_msg_ids = pending_info.get("user_message_ids", [])
            admin_msg_id = pending_info.get("admin_message_id")
            
            logging.info(f"Top up untuk user {user_id} sebesar {unique_amount} telah kedaluwarsa di sisi user.")
            
                                                                           
            for msg_id in user_msg_ids:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                except Exception as e:
                                                                                         
                    if "message to delete not found" not in str(e):
                        logging.warning(f"Gagal menghapus pesan user {msg_id} untuk user {user_id}: {e}")

                                                                          
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Waktu pembayaran habis. Permintaan top up Anda telah kedaluwarsa. Jika sudah melakukan Top up tapi belum masuk harap hubungi admin."
            )
            
                                                                                      
            if admin_msg_id:
                try:
                                                                                      
                                                                            
                                                                                            
                    await context.bot.edit_message_text(
                        chat_id=ADMIN_ID,
                        message_id=admin_msg_id,
                        text=f"⌛️ Permintaan top up dari user `{user_id}` (Nominal unik: Rp{unique_amount:,}) *TELAH KEDALUWARSA DI SISI USER*.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("➕ Konfirmasi (Manual)", callback_data=f"admin_top_up_confirm_{user_id}_{pending_info.get('amount', 0)}"),
                            InlineKeyboardButton("❌ Tolak (Manual)", callback_data=f"admin_top_up_reject_{user_id}")
                        ]])                               
                    )
                except Exception as e:
                    logging.warning(f"Gagal mengedit pesan admin untuk top up kedaluwarsa {admin_msg_id}: {e}")
            
                                                                                             
                                                                            
            simpan_data_ke_db()                                                  

    except Exception as e:
        logging.error(f"Error pada schedule_top_up_expiration untuk user {user_id}: {e}", exc_info=True)
        
async def handle_top_up_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_details = user_data["registered_users"].get(str(user_id), {})

    if user_details.get("pending_top_up"):
        await update.message.reply_text(
            "Anda sudah memiliki permintaan top up yang aktif.\n\n"
            "• Jika sudah membayar, harap tunggu konfirmasi dari Admin.\n"
            "• Jika belum, selesaikan pembayaran atau tunggu hingga permintaan kedaluwarsa (5 menit) untuk membuat yang baru."
        )
        return

    try:
        top_up_amount = int(update.message.text.strip())
        
        if top_up_amount < MIN_TOP_UP_AMOUNT:
            await update.message.reply_text(f"Nominal top up minimal Rp{MIN_TOP_UP_AMOUNT:,}. Silakan masukkan lagi.", parse_mode="Markdown")
            context.user_data['next'] = 'handle_top_up_amount' 
            return

                                               
        random_suffix = random.randint(0, 100)
        unique_top_up_amount = top_up_amount + random_suffix

        status_msg = await update.message.reply_text("Sedang membuat kode pembayaran QRIS , harap tunggu...")
        
        try:
            if not QRIS_STATIS:
                raise ValueError("QRIS_STATIS belum diatur dengan benar di dalam kode bot.")

            response = requests.post("https://qrisku.my.id/api", json={"amount": str(unique_top_up_amount), "qris_statis": QRIS_STATIS}, timeout=20)
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get("status") == "success" and "qris_base64" in response_data:
                image_bytes = base64.b64decode(response_data["qris_base64"])
                await status_msg.delete()
                
                photo_msg = await context.bot.send_photo(chat_id=user_id, photo=image_bytes)
                text_msg = await context.bot.send_message(user_id, f"Harap bayar sebesar *Rp{unique_top_up_amount:,}* ke QRIS di atas.\n\nKode pembayaran ini akan kedaluwarsa dalam 5 menit.", parse_mode="Markdown")
                
                user_info = user_details
                admin_notification_text = (
                    f"💰 *Permintaan Top Up Baru!* 💰\n"
                    f"User: `{user_info.get('first_name', 'N/A')}` (`@{user_info.get('username', 'N/A')}` / `{user_id}`)\n"
                    f"Nominal asli: *Rp{top_up_amount:,}*\n"
                    f"Nominal unik: *Rp{unique_top_up_amount:,}* (Kode unik: `{random_suffix}`)" 
                )
                keyboard_admin = [[InlineKeyboardButton(f"➕ Konfirmasi", callback_data=f"admin_top_up_confirm_{user_id}_{top_up_amount}"),
                                   InlineKeyboardButton(f"❌ Tolak", callback_data=f"admin_top_up_reject_{user_id}")]]
                admin_msg = await context.bot.send_message(ADMIN_ID, admin_notification_text, reply_markup=InlineKeyboardMarkup(keyboard_admin), parse_mode="Markdown")

                pending_info = {
                    "amount": top_up_amount,
                    "unique_amount": unique_top_up_amount,
                    "user_message_ids": [photo_msg.message_id, text_msg.message_id],
                    "admin_message_id": admin_msg.message_id
                }
                user_data["registered_users"][str(user_id)]["pending_top_up"] = pending_info
                simpan_data_ke_db()

                asyncio.create_task(schedule_top_up_expiration(context, user_id, unique_top_up_amount))
            else:
                raise ValueError(f"API QRIS mengembalikan error: {response_data.get('message')}")

        except Exception as e:
            logging.error(f"Gagal membuat kode pembayaran QRIS : {e}", exc_info=True)
            await status_msg.edit_text("Gagal membuat kode pembayran QRIS. Mohon coba lagi atau hubungi admin.")
            return

    except ValueError:
        await update.message.reply_text("Nominal tidak valid. Masukkan angka saja.", parse_mode="Markdown")
        context.user_data['next'] = 'handle_top_up_amount'
    return        

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID and 'next' in context.user_data and context.user_data['next'].startswith('admin_'):
        next_admin_step = context.user_data.pop('next')

                                                                                                        
        if next_admin_step not in ['admin_handle_broadcast_exclusions', 'admin_handle_search_user_input', 'admin_handle_check_user_transactions_input', 'admin_handle_search_api_package_input']:
             await delete_last_message(user_id, context)

        if next_admin_step == 'admin_handle_add_balance_input':
            await admin_handle_add_balance_input(update, context)
        elif next_admin_step == 'admin_handle_deduct_balance_input':
            await admin_handle_deduct_balance_input(update, context)
        elif next_admin_step == 'admin_handle_block_user_input':
            await admin_handle_block_user_input(update, context)
        elif next_admin_step == 'admin_handle_unblock_user_input':
            await admin_handle_unblock_user_input(update, context)
        elif next_admin_step == 'admin_handle_broadcast_message_content':
            await admin_handle_broadcast_message_content(update, context)
            return                                                     
        elif next_admin_step == 'admin_handle_broadcast_exclusions':
            await admin_handle_broadcast_exclusions(update, context)
            return                                                   
        elif next_admin_step == 'admin_handle_search_user_input':
            await admin_handle_search_user_input(update, context)
        elif next_admin_step == 'admin_handle_check_user_transactions_input':
            await admin_handle_check_user_transactions_input(update, context)
        elif next_admin_step == 'admin_handle_search_api_package_input':
            await admin_handle_search_api_package_input(update, context)     
        elif next_admin_step == 'admin_handle_smart_package_code_input':
            await admin_handle_smart_package_code_input(update, context)
        elif next_admin_step == 'admin_handle_smart_package_display_name_input':
            await admin_handle_smart_package_display_name_input(update, context)
        elif next_admin_step == 'admin_handle_smart_package_price_input':
            await admin_handle_smart_package_price_input(update, context)
        elif next_admin_step == 'admin_handle_smart_package_ewallet_fee_input':
            await admin_handle_smart_package_ewallet_fee_input(update, context)
        elif next_admin_step == 'admin_handle_smart_package_desc_and_save':
            await admin_handle_smart_package_desc_and_save(update, context)
        elif next_admin_step == 'admin_edit_custom_package_name_input':
            package_code = context.user_data.get('editing_package_code')
            if not package_code:
                await update.message.reply_text("Terjadi kesalahan (kode paket tidak ditemukan). Silakan mulai ulang.")
                await admin_menu(update, context)
                return

            new_name = update.message.text.strip()
            if new_name.upper() == 'SKIP':
                new_name = user_data["custom_packages"][package_code]['name']

            context.user_data['temp_edited_name'] = new_name
            await context.bot.send_message(user_id, f"Masukkan harga baru untuk paket ini (angka saja, cth: `5000`) atau ketik `SKIP` untuk tidak mengubah harga:")
            context.user_data['next'] = 'admin_edit_custom_package_price_input'

        elif next_admin_step == 'admin_edit_custom_package_price_input':
            package_code = context.user_data.pop('editing_package_code', None)
            new_name = context.user_data.pop('temp_edited_name', None)
            new_price_str = update.message.text.strip()

            if package_code is None or new_name is None:
                await update.message.reply_text("Terjadi kesalahan. Silakan mulai ulang pengeditan paket kustom.")
                await admin_menu(update, context)
                return

            original_price = user_data["custom_packages"][package_code]['price']
            new_price = original_price

            if new_price_str.upper() != 'SKIP':
                try:
                    new_price = int(new_price_str)
                    if new_price <= 0:
                        await update.message.reply_text("Harga harus lebih besar dari 0. Masukkan harga baru (angka saja) atau `SKIP`:")
                        context.user_data['editing_package_code'] = package_code                          
                        context.user_data['temp_edited_name'] = new_name                          
                        context.user_data['next'] = 'admin_edit_custom_package_price_input'
                        return
                except ValueError:
                    await update.message.reply_text("Harga tidak valid. Masukkan angka saja atau `SKIP`.")
                    context.user_data['editing_package_code'] = package_code                          
                    context.user_data['temp_edited_name'] = new_name                          
                    context.user_data['next'] = 'admin_edit_custom_package_price_input'
                    return

            user_data["custom_packages"][package_code]['name'] = new_name
            user_data["custom_packages"][package_code]['price'] = new_price
            simpan_data_ke_db()
            await update.message.reply_text(f"✅ Paket `{package_code}` berhasil diperbarui:\nNama: *{new_name}*\nHarga: Rp{new_price:,}", parse_mode="Markdown")
            await admin_menu(update, context)
        elif next_admin_step == 'admin_handle_delete_custom_package_confirmation':
            package_code_to_delete = context.user_data.pop('confirm_delete_package_code', None)
            confirmation = update.message.text.strip().upper()

            if package_code_to_delete is None:
                await update.message.reply_text("Kesalahan konfirmasi penghapusan. Silakan coba lagi dari menu edit paket kustom.")
                await admin_menu(update, context)
                return

            if confirmation == 'YA':
                if package_code_to_delete in user_data["custom_packages"]:
                    del user_data["custom_packages"][package_code_to_delete]
                    simpan_data_ke_db()
                    await update.message.reply_text(f"✅ Paket kustom `{package_code_to_delete}` berhasil dihapus.")
                else:
                    await update.message.reply_text(f"❌ Paket kustom `{package_code_to_delete}` tidak ditemukan.")
            else:
                await update.message.reply_text("Penghapusan paket kustom dibatalkan.")
            await admin_menu(update, context)
        return

    if not await check_access(update, context):
        return

    if 'next' in context.user_data and context.user_data['next'] == 'handle_user_broadcast_reply':
        next_step = context.user_data.pop('next')
        await delete_last_message(user_id, context)

        reply_text = update.message.text
        user_details = user_data["registered_users"].get(str(user_id), {})

        user_first_name = user_details.get("first_name", "N/A")
        user_username = user_details.get("username", "N/A")
        user_balance = user_details.get("balance", 0)

        admin_notification = (
            f"📩 *Jawaban Broadcast Diterima* 📩\n"
            f"👤 *Nama User:* `{user_first_name}`\n"
            f"🆔 *ID User:* `{user_id}`\n"
            f"🔗 *Username:* `@{user_username}`\n"
            f"💰 *Sisa Saldo User:* `Rp{user_balance:,}`\n"
            f"💬 *Isi Pesan Jawaban:*\n"
            f"{reply_text}"
        )

        try:
            await context.bot.send_message(ADMIN_ID, admin_notification, parse_mode="Markdown")
            await update.message.reply_text("✅ Jawaban Anda telah berhasil dikirim ke admin. Terima kasih!")
        except Exception as e:
            logging.error(f"Gagal mengirim jawaban broadcast ke admin dari user {user_id}: {e}")
            await update.message.reply_text("❌ Maaf, terjadi kesalahan saat mengirim jawaban Anda. Coba lagi nanti.")

        await send_main_menu(update, context)
        return

    if 'next' not in context.user_data:
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    next_step = context.user_data.pop('next')

    if next_step == 'handle_cek_kuota_baru_input':
        await jalankan_cek_kuota_baru(update, context)
        return

    if next_step == 'handle_phone_for_login':
        phone = update.message.text.strip()
        if phone.startswith('08'):
            phone = '62' + phone[1:]

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_phone_for_login'
            return

        context.user_data['temp_phone_for_login'] = phone
        logging.info(f"User {user_id} mengirim nomor untuk login: {phone}")

        login_provider = context.user_data.get('current_login_provider', 'kmsp')
        if login_provider == 'kmsp':
            await request_otp_and_prompt_kmsp(update, context, phone)
        elif login_provider == 'hesda':
            await request_otp_and_prompt_hesda(update, context, phone)

                                                        
    elif next_step == 'handle_phone_for_hesda_batch_purchase':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_phone_for_hesda_batch_purchase'
            return
            
                                            
                                                               
        access_token_hesda = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur Batch BYPAS untuk {phone}. Mencari token BYPAS di seluruh database...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get("hesda", {}).get("access_token")
                if token:
                    access_token_hesda = token
                    logging.info(f"Token BYPAS untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token_hesda:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token_hesda = token_data.get("hesda", {}).get("access_token")

        if not access_token_hesda:
            total_price_to_refund = context.user_data.pop('total_hesdapkg_batch_price', 0)
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken BYPAS tidak ditemukan untuk nomor `{phone}` di seluruh database.", parse_mode="Markdown")
                if total_price_to_refund > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += total_price_to_refund
                    simpan_data_ke_db()
                    await context.bot.send_message(user_id, f"💰 Saldo Anda sebesar Rp{total_price_to_refund:,} telah dikembalikan.", parse_mode="Markdown")
                await send_main_menu(update, context)
            else:
                await update.message.reply_text(f"Token BYPAS tidak ditemukan untuk nomor `{phone}`. Silakan login terlebih dahulu.")
                if total_price_to_refund > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += total_price_to_refund
                    simpan_data_ke_db()
                    await context.bot.send_message(user_id, f"💰 Saldo Anda sebesar Rp{total_price_to_refund:,} telah dikembalikan.", parse_mode="Markdown")
                          
                context.user_data['temp_phone_for_login'] = phone
                context.user_data['current_login_provider'] = 'hesda'
                context.user_data['next'] = 'handle_login_otp_input'
                context.user_data['resume_hesda_purchase_after_otp'] = True
                await request_otp_and_prompt_hesda(update, context, phone)
            return
                                            

        context.user_data['phone_for_hesda_batch'] = phone
        selected_package_ids = user_data["registered_users"][str(user_id)].get("selected_hesdapkg_ids", [])
        user_data["registered_users"][str(user_id)]["selected_hesdapkg_ids"] = []

        context.user_data['packages_to_process_hesda_batch'] = selected_package_ids
        context.user_data['current_batch_index_hesda'] = 0
        context.user_data['current_hesda_batch_results'] = []

        asyncio.create_task(process_hesda_package_queue(update, context))
        return

    elif next_step == 'handle_automatic_xcs_addon_phone_input':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_automatic_xcs_addon_phone_input'
            return

        automatic_xcs_flow_state = context.user_data.get('automatic_xcs_flow_state')
        if not automatic_xcs_flow_state:
            await update.message.reply_text("Sesi pembelian otomatis XCS ADD ON tidak valid atau kedaluwarsa. Silakan mulai ulang.")
            await send_main_menu(update, context)
            return

        automatic_xcs_flow_state['phone'] = phone
        access_token_kmsp = None

                                            

                                             
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur XCS otomatis untuk nomor {phone}. Mencari token di seluruh database...")
            
                                                  
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get("kmsp", {}).get("access_token")
                if token:
                    access_token_kmsp = token
                    logging.info(f"Token untuk nomor {phone} ditemukan di akun user {uid}. Admin akan menggunakan token ini.")
                    break                                                
        
                                                                                                              
        if not access_token_kmsp:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token_kmsp = token_data.get("kmsp", {}).get("access_token")

                                            

        if not access_token_kmsp:
                                                                                                              
                                                                    
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken LOGIN tidak ditemukan untuk nomor `{phone}` di seluruh database bot. Nomor ini belum pernah login oleh siapapun.", parse_mode="Markdown")
                                                                                    
                total_price = context.user_data.pop('total_automatic_xcs_price', 0)
                if total_price > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += total_price
                    simpan_data_ke_db()
                    await context.bot.send_message(user_id, f"💰 Saldo Anda sebesar Rp{total_price:,} telah dikembalikan.", parse_mode="Markdown")
                await send_main_menu(update, context)                        
            else:
                                                  
                await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor `{phone}`. Silakan login terlebih dahulu untuk nomor ini.")
                context.user_data['temp_phone_for_login'] = phone
                context.user_data['current_login_provider'] = 'kmsp'
                context.user_data['next'] = 'handle_login_otp_input'
                context.user_data['resume_automatic_xcs_purchase_after_otp'] = True
                await request_otp_and_prompt_kmsp(update, context, phone)
            return

                                                                                                            
        automatic_xcs_flow_state['access_token'] = access_token_kmsp
        simpan_data_ke_db()

        await context.bot.send_message(user_id, f"Memulai proses pembelian XCS ADD ON Otomatis untuk nomor *{phone}*.\n\nMemproses paket ADD ON pertama...", parse_mode="Markdown")
        asyncio.create_task(run_automatic_xcs_addon_flow(update, context))
        return

    elif next_step == 'handle_automatic_xutp_phone_input':                                                      
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_automatic_xutp_phone_input'
            return

        payment_method_selected = context.user_data.get('xutp_purchase_payment_method', 'DANA')

                                            
        access_token_kmsp = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur XUTP untuk {phone}. Mencari token KMSP di seluruh database...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get("kmsp", {}).get("access_token")
                if token:
                    access_token_kmsp = token
                    logging.info(f"Token KMSP untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token_kmsp:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token_kmsp = token_data.get("kmsp", {}).get("access_token")
                                            

        if not access_token_kmsp:
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken LOGIN tidak ditemukan untuk nomor `{phone}` di seluruh database bot.", parse_mode="Markdown")
                await send_main_menu(update, context)
            else:
                await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor `{phone}`. Silakan login terlebih dahulu untuk nomor ini.")
                context.user_data['temp_phone_for_login'] = phone
                context.user_data['current_login_provider'] = 'kmsp'
                context.user_data['next'] = 'handle_login_otp_input'
                context.user_data['resume_automatic_xutp_purchase_after_otp'] = True           
                await request_otp_and_prompt_kmsp(update, context, phone)
            return

        context.user_data['xutp_purchase_phone'] = phone
        context.user_data['xutp_purchase_token'] = access_token_kmsp
        context.user_data['xutp_purchase_payment_method'] = payment_method_selected
        
        if 'xutp_flow_state' in user_data["registered_users"].get(str(user_id), {}).get('accounts', {}).get(phone, {}):
             del user_data["registered_users"][str(user_id)]['accounts'][phone]['xutp_flow_state']
        simpan_data_ke_db()

        await context.bot.send_message(user_id, f"Memulai proses pembelian XUTP otomatis untuk nomor *{phone}* dengan metode *{payment_method_selected}*.\n\nMemproses paket awal (ADD ON PREMIUM)...", parse_mode="Markdown")
        asyncio.create_task(run_automatic_xutp_flow(update, context))
        return

    elif next_step == 'handle_phone_for_30h_batch_purchase':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_phone_for_30h_batch_purchase'
            return

                                            
        access_token_kmsp = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur Batch 30H untuk {phone}. Mencari token KMSP di seluruh database...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get("kmsp", {}).get("access_token")
                if token:
                    access_token_kmsp = token
                    logging.info(f"Token KMSP untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token_kmsp:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token_kmsp = token_data.get("kmsp", {}).get("access_token")

        if not access_token_kmsp:
            total_price_to_refund = context.user_data.pop('total_30h_batch_price', 0)
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken LOGIN tidak ditemukan untuk nomor `{phone}` di seluruh database.", parse_mode="Markdown")
                if total_price_to_refund > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += total_price_to_refund
                    simpan_data_ke_db()
                    await context.bot.send_message(user_id, f"💰 Saldo Anda sebesar Rp{total_price_to_refund:,} telah dikembalikan.", parse_mode="Markdown")
                await send_main_menu(update, context)
            else:
                await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor `{phone}`. Silakan login terlebih dahulu.")
                if total_price_to_refund > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += total_price_to_refund
                    simpan_data_ke_db()
                    await context.bot.send_message(user_id, f"💰 Saldo Anda sebesar Rp{total_price_to_refund:,} telah dikembalikan.", parse_mode="Markdown")
                context.user_data['temp_phone_for_login'] = phone
                context.user_data['current_login_provider'] = 'kmsp'
                context.user_data['next'] = 'handle_login_otp_input'
                context.user_data['resume_30h_purchase_after_otp'] = True
                await request_otp_and_prompt_kmsp(update, context, phone)
            return
        
                                     
                                                                                         
        context.user_data['token_for_30h_batch'] = access_token_kmsp
                                  

        context.user_data['phone_for_30h_batch'] = phone
        selected_package_ids = user_data["registered_users"][str(user_id)].get("selected_30h_pkg_ids", [])
        user_data["registered_users"][str(user_id)]["selected_30h_pkg_ids"] = []

        context.user_data['packages_to_process_30h_batch'] = selected_package_ids
        context.user_data['current_batch_index_30h'] = 0
        context.user_data['current_30h_batch_results'] = []

        logging.info(f"Starting 30H batch purchase for user {user_id} with phone {phone}. Packages: {selected_package_ids}")
        asyncio.create_task(process_30h_package_queue(update, context))
        return

    elif next_step == 'handle_akun_saya_nomor_input':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            await update.message.reply_text("Format nomor HP salah. Masukkan lagi atau kembali ke menu utama.")
            context.user_data['next'] = 'handle_akun_saya_nomor_input'
            return

                                                                      
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        nomor_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone)

        if nomor_data:
            kmsp_status = "✅" if nomor_data.get("kmsp", {}).get("access_token") else "❌"
            hesda_status = "✅" if nomor_data.get("hesda", {}).get("access_token") else "❌"

            timestamp_str = "N/A"
            ts_iso = nomor_data.get("kmsp", {}).get("login_timestamp") or nomor_data.get("hesda", {}).get("login_timestamp")
            if ts_iso:
                try:
                    dt_object = datetime.fromisoformat(ts_iso)
                    timestamp_str = dt_object.strftime('%H.%M  %d.%m.%Y')
                except ValueError:
                    timestamp_str = "Format waktu tidak valid"

            response_text = (
                f"Nomor kamu terdeteksi\n"
                f"`{phone}`   `{timestamp_str}`\n\n"
                f"*Status Nomor*\n"
                f"LOGIN OTP {kmsp_status}\n"
                f"OTP BYPAS {hesda_status}\n\n"
                f"_Meskipun nomor kamu sudah pernah login, jika XL merefresh token login, besar kemungkinan kamu mesti login otp ulang._"
            )
                                                                 
            await update.message.reply_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            response_text = f"❌ Nomor `{phone}` tidak ditemukan di riwayat login Anda. Silakan login terlebih dahulu untuk nomor ini."
                                                                 
            await update.message.reply_text(response_text, parse_mode="Markdown", reply_markup=reply_markup)
            
                                                                 
                                                
        return

    elif next_step == 'handle_beli_single_vidio_package':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_beli_single_vidio_package'
            return

        kode = context.user_data.pop('selected_package_code')
        package_name_display = context.user_data.pop('selected_package_name_display')
        metode = context.user_data.pop('selected_payment_method')
        price_lookup_key = context.user_data.pop('selected_price_lookup_key')
        api_provider = context.user_data.get('selected_api_provider', 'kmsp')

        if not kode or not package_name_display or not metode or price_lookup_key is None:
            await update.message.reply_text("Informasi paket tidak lengkap. Silakan pilih ulang paket.")
            await send_main_menu(update, context)
            return

                                            
        access_token = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur Vidio XL untuk {phone}. Mencari token KMSP di database...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get(api_provider, {}).get("access_token")
                if token:
                    access_token = token
                    logging.info(f"Token KMSP untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token = token_data.get(api_provider, {}).get("access_token")
                                            

        required_balance = CUSTOM_PACKAGE_PRICES.get(price_lookup_key, {}).get('price_bot', 0)

        if not access_token:
            if user_id == ADMIN_ID:
                 await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken LOGIN tidak ditemukan untuk `{phone}` di database.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor ini. Silakan login terlebih dahulu.")
                await context.bot.send_message(user_id, "Silakan login untuk LOGIN.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("LOGIN OTP", callback_data="login_kmsp")]]))
            return

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        if user_current_balance < required_balance:
            await context.bot.send_message(user_id, f"❌ Saldo Anda tidak cukup untuk membeli paket: *{package_name_display}* (harga: Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_current_balance:,}.", parse_mode="Markdown")
            await send_vidio_xl_menu(update, context)
            return

        if required_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] -= required_balance
            simpan_data_ke_db()
            await update.message.reply_text(f"Memproses pembelian... Saldo Anda terpotong: *Rp{required_balance:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
            logging.info(f"Saldo user {user_id} dipotong sebesar {required_balance} untuk paket {package_name_display}.")
        else:
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await context.bot.send_message(user_id, f"❌ MESKIPUN PAKET GRATIS, ANDA HARUS MEMILIKI MINIMAL SALDO BOT Rp{MIN_BALANCE_FOR_PURCHASE:,} (Saldo Anda saat ini: Rp{user_current_balance:,}).", parse_mode="Markdown")
                await send_vidio_xl_menu(update, context)
                return

        await asyncio.create_task(execute_single_purchase(
            update, context, user_id, kode, phone, access_token, metode,
            deducted_balance=required_balance,
            return_menu_callback_data="vidio_xl_menu",
            provider=api_provider,
            package_name_for_display=package_name_display
        ))

    elif next_step == 'handle_beli_single_iflix_package':                     
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_beli_single_iflix_package'                          
            return

        kode = context.user_data.pop('selected_package_code') 
        package_name_display = context.user_data.pop('selected_package_name_display') 
        metode = context.user_data.pop('selected_payment_method') 
        price_lookup_key = context.user_data.pop('selected_price_lookup_key') 
        api_provider = context.user_data.get('selected_api_provider', 'kmsp')

        if not kode or not package_name_display or not metode or price_lookup_key is None:
            await update.message.reply_text("Informasi paket tidak lengkap. Silakan pilih ulang paket.")
            await send_main_menu(update, context)
            return

        token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
        access_token = token_data.get(api_provider, {}).get("access_token")

        if not access_token:
            await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor ini. Silakan login terlebih dahulu.")
            required_balance_for_refund = CUSTOM_PACKAGE_PRICES.get(price_lookup_key)
            if required_balance_for_refund is not None and required_balance_for_refund > 0:
                user_data["registered_users"][str(user_id)]["balance"] += required_balance_for_refund
                simpan_data_ke_db()
                await context.bot.send_message(user_id, f"Saldo Anda sebesar *Rp{required_balance_for_refund:,}* telah dikembalikan karena token tidak ditemukan.", parse_mode="Markdown")

            await context.bot.send_message(user_id, "Silakan login untuk LOGIN.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("LOGIN OTP", callback_data="login_kmsp")]]))
            return

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        required_balance = CUSTOM_PACKAGE_PRICES.get(price_lookup_key, {}).get('price_bot', 0)

        if user_current_balance < required_balance:
            await context.bot.send_message(user_id, f"❌ Saldo Anda tidak cukup untuk membeli paket: *{package_name_display}* (harga: Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_current_balance:,}.", parse_mode="Markdown")
            await send_iflix_xl_menu(update, context)                           
            return

        if required_balance > 0: 
            user_data["registered_users"][str(user_id)]["balance"] -= required_balance
            simpan_data_ke_db()
            await update.message.reply_text(f"Memproses pembelian... Saldo Anda terpotong: *Rp{required_balance:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
            logging.info(f"Saldo user {user_id} dipotong sebesar {required_balance} untuk paket {package_name_display}.")
        else: 
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await context.bot.send_message(user_id, f"❌ MESKIPUN PAKET GRATIS, ANDA HARUS MEMILIKI MINIMAL SALDO BOT Rp{MIN_BALANCE_FOR_PURCHASE:,} (Saldo Anda saat ini: Rp{user_current_balance:,}).", parse_mode="Markdown")
                await send_iflix_xl_menu(update, context)                           
                return

        await asyncio.create_task(execute_single_purchase(
            update, context, user_id, kode, phone, access_token, metode,
            deducted_balance=required_balance, 
            return_menu_callback_data="iflix_xl_menu",                           
            provider="kmsp",
            package_name_for_display=package_name_display 
        ))

    elif next_step == 'handle_login_otp_input':
        otp_input = update.message.text.strip()
        if not otp_input.isdigit():
            msg = await context.bot.send_message(user_id, "Format OTP salah. Masukkan hanya angka.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_login_otp_input'
            return

        phone = user_data.get("registered_users", {}).get(str(user_id), {}).get('current_phone')
        if not phone:
            msg = await context.bot.send_message(user_id, "Nomor HP tidak ditemukan. Silakan coba Login ulang.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            await send_main_menu(update, context)
            return

        current_provider = context.user_data.get('current_login_provider')
        stored_auth_id = user_data["registered_users"][str(user_id)]['accounts'].get(phone, {}).get(current_provider, {}).get('auth_id')

        if not stored_auth_id:
            msg = await context.bot.send_message(user_id, f"Auth ID tidak ditemukan untuk nomor ini. Silakan coba Login kembali.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            await send_main_menu(update, context)
            return

        login_counter[user_id] = login_counter.get(user_id, 0) + 1
        if login_counter[user_id] > 3:
            msg = await context.bot.send_message(user_id, "Anda telah melebihi batas percobaan OTP. Silakan mulai ulang proses Login.")
            del login_counter[user_id]
            await send_main_menu(update, context)
            return

        try:
            if current_provider == 'kmsp':
                url = f"https://golang-openapi-login-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&phone={phone}&method=OTP&auth_id={stored_auth_id}&otp={otp_input}"
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                result = response.json()
                data_login = result.get('data')

                logging.info(f"Response Login OTP KMSP for {phone}: {result}")

                if not data_login or 'access_token' not in data_login:
                    api_error_message = result.get("message", "Login gagal. Respons tidak valid atau token tidak ditemukan.")
                    raise ValueError(api_error_message)

                access_token = data_login['access_token']
                user_data["registered_users"][str(user_id)]['accounts'][phone]['kmsp']['access_token'] = access_token
                                             
                user_data["registered_users"][str(user_id)]['accounts'][phone]['kmsp']['login_timestamp'] = datetime.now().isoformat()
                simpan_data_ke_db()
                logging.info(f"User {user_id} login KMSP berhasil dengan nomor {phone}. Token: {access_token[:10]}...")

                await context.bot.send_message(user_id, f"✅ *Login OTP Berhasil!* Nomor *{phone}* telah terhubung.", parse_mode="Markdown")
                await context.bot.send_message(ADMIN_ID, f"⚠️ User `{user_id}` (`{update.effective_user.first_name or 'N/A'}`) login OTP LOGIN berhasil untuk nomor `{phone}`.", parse_mode="Markdown")

            elif current_provider == 'hesda':
                url = "https://api.hesda-store.com/v2/login_sms"
                headers = get_hesda_auth_headers()
                if not headers:
                    raise ValueError("Informasi otentikasi tidak lengkap.")

                payload = {
                    "hesdastore": HESDA_API_KEY,
                    "no_hp": phone,
                    "metode": "OTP",
                    "auth_id": stored_auth_id,
                    "kode_otp": otp_input
                }

                response = requests.post(url, headers=headers, data=payload, timeout=20)
                response.raise_for_status()
                result = response.json()
                data_login = result.get('data')

                logging.info(f"Response Login OTP Hesda for {phone}: {result}")

                if not data_login or 'access_token' not in data_login:
                    api_error_message = result.get("message", "Login gagal. Respons tidak valid atau token tidak ditemukan.")
                    raise ValueError(api_error_message)

                access_token = data_login['access_token']
                user_data["registered_users"][str(user_id)]['accounts'][phone]['hesda']['access_token'] = access_token
                                             
                user_data["registered_users"][str(user_id)]['accounts'][phone]['hesda']['login_timestamp'] = datetime.now().isoformat()
                simpan_data_ke_db()
                logging.info(f"User {user_id} login Hesda berhasil dengan nomor {phone}. Token: {access_token[:10]}...")

                await context.bot.send_message(user_id, f"✅ *Login BYPAS Berhasil!* Nomor *{phone}* telah terhubung.", parse_mode="Markdown")
                await context.bot.send_message(ADMIN_ID, f"⚠️ User `{user_id}` (`{update.effective_user.first_name or 'N/A'}`) login OTP BYPAS berhasil untuk nomor `{phone}`.", parse_mode="Markdown")

            del login_counter[user_id]

            if context.user_data.pop('resume_hesda_purchase_after_otp', False):
                pending_package_details = context.user_data.pop('pending_hesda_package_details', None)
                if pending_package_details:
                    selected_package_id = pending_package_details['id']
                    package_name = pending_package_details['name']
                    required_balance = pending_package_details['price_bot']
                    payment_method = pending_package_details['payment_method']
                    return_menu_callback_data = pending_package_details['return_menu']

                    user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
                    if user_current_balance < required_balance:
                        await context.bot.send_message(user_id, f"❌ Saldo Anda tidak cukup untuk membeli paket: *{package_name}* (harga bot: Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_current_balance:,}.", parse_mode="Markdown")
                        await send_bypass_menu(update, context)
                        return

                    if required_balance > 0:
                        user_data["registered_users"][str(user_id)]["balance"] -= required_balance
                        simpan_data_ke_db()
                        await context.bot.send_message(user_id, f"Melanjutkan pembelian *{package_name}*...\nSaldo Anda terpotong: *Rp{required_balance:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
                        logging.info(f"Saldo user {user_id} dipotong sebesar {required_balance} untuk paket BYPAS {package_name} (setelah OTP).")
                    else:
                        if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                            await context.bot.send_message(user_id, f"❌ MESKIPUN PAKET GRATIS, ANDA HARUS MEMILIKI MINIMAL SALDO BOT Rp{MIN_BALANCE_FOR_PURCHASE:,} (Saldo Anda saat ini: Rp{user_current_balance:,}).", parse_mode="Markdown")
                            await send_bypass_menu(update, context)
                            return

                    asyncio.create_task(execute_single_purchase_hesda(update, context, user_id, selected_package_id, package_name, phone, access_token, payment_method, required_balance, return_menu_callback_data))
                elif 'packages_to_process_hesda_batch' in context.user_data:
                    logging.info(f"Resuming Hesda batch purchase for user {user_id} after OTP.")
                    asyncio.create_task(process_hesda_package_queue(update, context))
                else:
                    await context.bot.send_message(user_id, "Terjadi kesalahan: data pembelian BYPAS tidak ditemukan setelah OTP. Silakan coba lagi dari awal.")
                    await send_bypass_menu(update, context)
            elif context.user_data.pop('resume_30h_purchase_after_otp', False):
                logging.info(f"Resuming 30H batch purchase for user {user_id} after KMSP OTP.")
                asyncio.create_task(process_30h_package_queue(update, context))
            elif context.user_data.pop('resume_automatic_purchase_after_otp', False):
                logging.info(f"Resuming automatic purchase flow for user {user_id} after KMSP OTP.")
                asyncio.create_task(run_automatic_purchase_flow(update, context))
            elif context.user_data.pop('resume_automatic_xutp_purchase_after_otp', False):
                logging.info(f"Resuming automatic XUTP purchase flow for user {user_id} after KMSP OTP.")
                asyncio.create_task(run_automatic_xutp_flow(update, context))
            else:
                await send_main_menu(update, context)

        except requests.exceptions.HTTPError as http_err:
            error_detail = http_err.response.json().get("message", "unknown error") if http_err.response.content else "no response content"
            logging.error(f"HTTP error saat login OTP {current_provider} untuk {phone}: {http_err}. Respon: {http_err.response.text}. Detail: {error_detail}")
            msg = await context.bot.send_message(user_id, f"OTP salah atau kedaluwarsa. Terjadi kesalahan saat login: {error_detail}. Mohon coba lagi atau minta OTP baru.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_login_otp_input'
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error saat login OTP {current_provider} untuk {phone}: {e}")
            msg = await context.bot.send_message(user_id, f"Terjadi kesalahan jaringan saat login. Mohon coba lagi nanti.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            await send_main_menu(update, context)
        except json.JSONDecodeError:
            logging.error(f"Gagal mengurai JSON dari respon login OTP {current_provider}. Respon: {response.text}")
            msg = await context.bot.send_message(user_id, f"Terjadi kesalahan saat memproses data login (JSON tidak valid). Cek kembali OTP Anda.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_login_otp_input'
        except ValueError as e:
            logging.error(f"Kesalahan logika login {current_provider}: {e}")
            msg = await context.bot.send_message(user_id, f"Login gagal: {e}.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_login_otp_input'
        except Exception as e:
            logging.error(f"Kesalahan tak terduga saat login {current_provider}: {e}", exc_info=True)
            msg = await context.bot.send_message(user_id, f"Terjadi kesalahan tak terduga saat login. Silakan laporkan ini kepada admin.")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            await send_main_menu(update, context)
            
    elif next_step == 'handle_top_up_amount':
        await handle_top_up_amount(update, context)
        return

    elif next_step == 'handle_all_addons_phone_input':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_all_addons_phone_input'
            return

        context.user_data['phone_for_all_addons'] = phone
        asyncio.create_task(process_addon_batch(update, context))
        return

    elif next_step == 'handle_beli_xcp' or next_step == 'handle_beli_uts_package':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = next_step
            return

        kode = context.user_data.get('selected_package_code')
        metode = context.user_data.get('selected_payment_method', "DANA")
        api_provider = context.user_data.get('selected_api_provider', 'kmsp')

        return_menu = None
        if next_step == 'handle_beli_xcp':
            if kode == XCP_8GB_PACKAGE['code']:
                return_menu = 'xcp_addon'
            else:
                return_menu = 'xcp_addon_dana'
        elif next_step == 'handle_beli_uts_package':
            return_menu = 'menu_uts_nested'

        if not kode:
            await update.message.reply_text("Informasi paket tidak lengkap. Silakan pilih ulang paket.")
            await send_main_menu(update, context)
            return

                                            
        access_token = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur {next_step} untuk {phone}. Mencari token {api_provider}...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get(api_provider, {}).get("access_token")
                if token:
                    access_token = token
                    logging.info(f"Token {api_provider} untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token = token_data.get(api_provider, {}).get("access_token")
                                            

        if not access_token:
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken {api_provider.upper()} tidak ditemukan untuk nomor `{phone}`.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Token {api_provider.upper()} tidak ditemukan untuk nomor ini. Silakan login terlebih dahulu.")
                if api_provider == 'kmsp':
                    await context.bot.send_message(user_id, "Silakan login untuk LOGIN.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("LOGIN OTP", callback_data="login")]]))
                elif api_provider == 'hesda':
                    await context.bot.send_message(user_id, "Silakan login untuk BYPAS.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Login BYPAS", callback_data="login_hesda")]]))
            return

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        required_balance = CUSTOM_PACKAGE_PRICES.get(kode, {}).get('price_bot', 0)

        if user_current_balance < required_balance:
            await context.bot.send_message(user_id, f"❌ Saldo Anda tidak cukup untuk membeli paket: *{kode}* (harga: Rp{required_balance:,}). Saldo Anda saat ini: Rp{user_current_balance:,}.", parse_mode="Markdown")
            if return_menu == 'xcp_addon': await send_xcp_addon_menu(update, context)
            elif return_menu == 'xcp_addon_dana': await send_xcp_addon_dana_menu(update, context)
            elif return_menu == 'menu_uts_nested': await send_uts_menu(update, context)
            else: await send_main_menu(update, context)
            return

        if required_balance > 0: 
            user_data["registered_users"][str(user_id)]["balance"] -= required_balance
            simpan_data_ke_db()
            await update.message.reply_text(f"Memproses pembelian... Saldo Anda terpotong: *Rp{required_balance:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
            logging.info(f"Saldo user {user_id} dipotong sebesar {required_balance} untuk paket {kode}.")
        else:
            if user_current_balance < MIN_BALANCE_FOR_PURCHASE:
                await context.bot.send_message(user_id, f"❌ MESKIPUN PAKET GRATIS, ANDA HARUS MEMILIKI MINIMAL SALDO BOT Rp{MIN_BALANCE_FOR_PURCHASE:,} (Saldo Anda saat ini: Rp{user_current_balance:,}).", parse_mode="Markdown")
                if return_menu == 'xcp_addon': await send_xcp_addon_menu(update, context)
                elif return_menu == 'xcp_addon_dana': await send_xcp_addon_dana_menu(update, context)
                elif return_menu == 'menu_uts_nested': await send_uts_menu(update, context)
                else: await send_main_menu(update, context)
                return

        asyncio.create_task(execute_single_purchase(update, context, user_id, kode, phone, access_token, metode, deducted_balance=required_balance, return_menu_callback_data=return_menu, provider=api_provider))

    elif next_step == 'handle_buy_custom_package_phone_input':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_buy_custom_package_phone_input'
            return

        package_code = context.user_data.pop('selected_custom_package_code', None)
        package_name = context.user_data.pop('selected_custom_package_name', None)
        package_price = context.user_data.pop('selected_custom_package_price', None)
        payment_method = context.user_data.pop('selected_custom_payment_method', 'BALANCE')
        api_provider = context.user_data.get('selected_api_provider', 'kmsp')

        if not all([package_code, package_name, package_price is not None]):
            await update.message.reply_text("Terjadi kesalahan dalam detail paket. Silakan coba lagi.")
            await send_main_menu(update, context)
            return

                                            
        access_token = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur Paket Kustom untuk {phone}. Mencari token {api_provider}...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get(api_provider, {}).get("access_token")
                if token:
                    access_token = token
                    logging.info(f"Token {api_provider} untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token = token_data.get(api_provider, {}).get("access_token")
                                            

        if not access_token:
                                                       
            user_data["registered_users"][str(user_id)]["balance"] += package_price
            simpan_data_ke_db()
            
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken {api_provider.upper()} tidak ditemukan untuk nomor `{phone}`.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Token {api_provider.upper()} tidak ditemukan untuk nomor ini. Silakan login terlebih dahulu.")
                if api_provider == 'kmsp':
                    await context.bot.send_message(user_id, "Silakan login untuk LOGIN.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("LOGIN OTP", callback_data="login")]]))
                elif api_provider == 'hesda':
                    await context.bot.send_message(user_id, "Silakan login untuk BYPAS.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Login BYPAS", callback_data="login_hesda")]]))
            return

        user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
        if user_current_balance < package_price:
            await update.message.reply_text(f"❌ Saldo Anda tidak cukup untuk membeli paket *{package_name}* (harga: Rp{package_price:,}).", parse_mode="Markdown")
            await send_main_menu(update, context)
            return

        user_data["registered_users"][str(user_id)]["balance"] -= package_price
        simpan_data_ke_db()
        await update.message.reply_text(f"Memproses pembelian paket kustom *{package_name}*...\nSaldo Anda terpotong: *Rp{package_price:,}*. Saldo tersisa: *Rp{user_data['registered_users'][str(user_id)]['balance']:,}*.", parse_mode="Markdown")
        logging.info(f"Saldo user {user_id} dipotong {package_price} untuk paket kustom {package_code}.")

        asyncio.create_task(execute_custom_package_purchase(
            update, context, user_id, package_code, package_name, 
            package_price, phone, access_token, payment_method, api_provider
        ))

    elif next_step == 'handle_automatic_purchase_phone_input':
        phone_raw = update.message.text.strip()
        if phone_raw.startswith('08'):
            phone = '62' + phone_raw[1:]
        else:
            phone = phone_raw

        if not re.match(r'^628\d{9,12}$', phone):
            msg = await context.bot.send_message(user_id, "Format nomor HP salah. Gunakan `08xxxxxxxxxx` atau `628xxxxxxxxxx`.", parse_mode="Markdown")
            bot_messages.setdefault(user_id, []).append(msg.message_id)
            context.user_data['next'] = 'handle_automatic_purchase_phone_input'
            return

        payment_method_selected = context.user_data.get('automatic_purchase_payment_method', 'DANA')

                                            
        access_token_kmsp = None
        if user_id == ADMIN_ID:
            logging.info(f"Admin ({user_id}) memulai alur Otomatis UTS/XC untuk {phone}. Mencari token KMSP...")
            for uid, details in user_data["registered_users"].items():
                token = details.get("accounts", {}).get(phone, {}).get("kmsp", {}).get("access_token")
                if token:
                    access_token_kmsp = token
                    logging.info(f"Token KMSP untuk {phone} ditemukan di akun user {uid}.")
                    break
        
        if not access_token_kmsp:
            token_data = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {})
            access_token_kmsp = token_data.get("kmsp", {}).get("access_token")
                                            

        if not access_token_kmsp:
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"❌ *Pencarian Gagal (Admin)*\n\nToken LOGIN tidak ditemukan untuk nomor `{phone}` di seluruh database.", parse_mode="Markdown")
                await send_main_menu(update, context)
            else:
                await update.message.reply_text(f"Token LOGIN tidak ditemukan untuk nomor `{phone}`. Silakan login terlebih dahulu untuk nomor ini.")
                context.user_data['temp_phone_for_login'] = phone
                context.user_data['current_login_provider'] = 'kmsp'
                context.user_data['next'] = 'handle_login_otp_input'
                context.user_data['resume_automatic_purchase_after_otp'] = True
                await request_otp_and_prompt_kmsp(update, context, phone)
            return

        context.user_data['automatic_purchase_phone'] = phone
        context.user_data['automatic_purchase_token'] = access_token_kmsp
        context.user_data['automatic_purchase_payment_method'] = payment_method_selected
        
        if 'automatic_flow_state' in user_data["registered_users"].get(str(user_id), {}).get('accounts', {}).get(phone, {}):
             del user_data["registered_users"][str(user_id)]['accounts'][phone]['automatic_flow_state']
        simpan_data_ke_db()

        await context.bot.send_message(user_id, f"Memulai proses pembelian Otomatis untuk nomor *{phone}* dengan metode *{payment_method_selected}*.\n\nMemproses paket XUTS...", parse_mode="Markdown")
        asyncio.create_task(run_automatic_purchase_flow(update, context))
        return

    elif next_step == 'handle_stop_paket_input':
        encrypted_package_code = update.message.text.strip()
        current_phone = user_data.get("registered_users", {}).get(str(user_id), {}).get("current_phone")
        access_token = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(current_phone, {}).get("kmsp", {}).get("access_token")

        if not access_token:
            await update.message.reply_text("Access token LOGIN tidak ditemukan. Silakan login terlebih dahulu.")
            await send_main_menu(update, context)
            return

        asyncio.create_task(execute_unreg_package(update, context, user_id, current_phone, access_token, encrypted_package_code))


async def process_addon_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['stop_batch_purchase'] = False

    phone = context.user_data.get('phone_for_all_addons')
    current_batch_num = context.user_data.get('addon_batch_current', 1)

    total_batches = math.ceil(len(ADD_ON_SEQUENCE) / ADDON_BATCH_SIZE)
    
    start_index = (current_batch_num - 1) * ADDON_BATCH_SIZE
    end_index = start_index + ADDON_BATCH_SIZE
    packages_in_batch = ADD_ON_SEQUENCE[start_index:end_index]
    
    if not packages_in_batch:
        await context.bot.send_message(user_id, "Tidak ada lagi paket Add-On untuk dibeli.")
        await send_xcp_addon_dana_menu(update, context)                       
        return

    stop_button_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏹️ Hentikan Proses", callback_data="stop_batch_purchase")]])
    status_message_text = f"⏳ Memulai *Batch {current_batch_num}/{total_batches}*...\nMohon jangan menutup chat atau menekan tombol lain."
    status_msg = await context.bot.send_message(user_id, status_message_text, parse_mode="Markdown", reply_markup=stop_button_keyboard)

    batch_results = []
    total_in_batch = len(packages_in_batch)
    for i, package_info in enumerate(packages_in_batch):
        if context.user_data.get('stop_batch_purchase'):
            await status_msg.edit_text("🛑 Proses pembelian batch dihentikan oleh pengguna.", reply_markup=None)
            return

        remaining_in_batch = total_in_batch - i
        await status_msg.edit_text(
            f"⏳ *Memproses Batch {current_batch_num}/{total_batches}...*\n"
            f"🛍️ Membeli paket *{package_info['name']}*...\n"
            f"📦 Sisa *{remaining_in_batch}* paket lagi di batch ini.",
            parse_mode="Markdown",
            reply_markup=stop_button_keyboard
        )
        
        purchase_result = await execute_package_purchase_for_batch(user_id, context, package_info, phone)
        batch_results.append(purchase_result)
        
        if i < total_in_batch - 1:
            if context.user_data.get('stop_batch_purchase'):
                break 

            delay_duration = 25
            info_text = "Mohon sabar, bot akan jeda 25 detik untuk menghindari transaksi pending di XL."
            status_after_purchase = "Berhasil" if purchase_result['success'] else f"Gagal ({purchase_result.get('error_message', 'Error')})"
            
            for t in range(delay_duration, 0, -1):
                if context.user_data.get('stop_batch_purchase'):
                    break
                try:
                    await status_msg.edit_text(
                        f"✅ *{package_info['name']}*: {status_after_purchase}.\n"
                        f"⏸️ Jeda *{t} detik* sebelum membeli paket berikutnya.\n"
                        f"_{info_text}_",
                        parse_mode="Markdown",
                        reply_markup=stop_button_keyboard
                    )
                except Exception as e:
                    if 'message is not modified' not in str(e):
                        logging.warning(f"Gagal edit pesan countdown batch: {e}")
                await asyncio.sleep(1)
    
    try:
        await status_msg.delete()
    except Exception:
        pass

    if context.user_data.get('stop_batch_purchase'):
        await context.bot.send_message(user_id, "🛑 Proses pembelian batch telah dihentikan.")
        await send_xcp_addon_dana_menu(update, context)                       
        return

    result_text_parts = [f"🏁 *Hasil Pembelian Batch {current_batch_num}/{total_batches}* 🏁\n"]
    keyboard = []
    
    for result in batch_results:
        if result['success']:
            result_text_parts.append(f"✅ *{result['package_name']}*: Berhasil diproses. Silakan bayar.")
            if result['deeplink']:
                keyboard.append([
                    InlineKeyboardButton(f"💰 Bayar {result['package_name']}", url=result['deeplink'])
                ])
        else:
            result_text_parts.append(f"❌ *{result['package_name']}*: Gagal - `{result['error_message']}`")
            if result['refunded_amount'] > 0:
                result_text_parts.append(f"   (Saldo Rp{result['refunded_amount']:,} telah dikembalikan).")

    final_result_text = "\n".join(result_text_parts)
    
    is_last_batch = (current_batch_num >= total_batches)
    if not is_last_batch:
        next_batch_num = current_batch_num + 1
        keyboard.append([InlineKeyboardButton(f"▶️ Lanjutkan ke Batch {next_batch_num}", callback_data=f"continue_addon_batch_{next_batch_num}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Paket XCS ADD ON", callback_data="xcp_addon_dana")])                       
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(user_id, final_result_text, parse_mode="Markdown", reply_markup=reply_markup)

async def execute_package_purchase_for_batch(user_id, context, package_info, phone):
    package_code = package_info['code']
    package_name = package_info['name']
    payment_method = "DANA"

                                                                                           
    access_token = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {}).get("kmsp", {}).get("access_token")

    if not access_token:
        return {"success": False, "package_name": package_name, "error_message": "Token LOGIN tidak ditemukan untuk nomor batch.", "refunded_amount": 0, "deeplink": None}
    
    required_balance = CUSTOM_PACKAGE_PRICES.get(package_code, 0)
    user_current_balance = user_data["registered_users"][str(user_id)]["balance"]
    
                                                                              
                                                                                                             
                                                   
                                                                 

    url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={package_code}&phone={phone}&access_token={access_token}&payment_method={payment_method}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list): result = result[0] if result else {}
        
        api_status = result.get('status', False)
        if not api_status:
            raise ValueError(result.get('message', 'API mengembalikan status gagal'))
        
        deeplink = result.get("data", {}).get("deeplink_data", {}).get("deeplink_url")
        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": "Pembelian Paket (Batch)", "package_code": package_code, "package_name": package_name, "phone": phone,
            "amount": -required_balance, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "status": "Berhasil",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()

        await context.bot.send_message(ADMIN_ID, f"BATCH-BUY: ✅ User {user_id} beli {package_name} utk {phone} (LOGIN).", parse_mode="Markdown")
        return {"success": True, "package_name": package_name, "error_message": None, "refunded_amount": 0, "deeplink": deeplink}

    except Exception as e:
        user_facing_error = "Error tidak diketahui"
        admin_facing_error = str(e)

        if isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Server terlalu lama merespon."
            admin_facing_error = "Read timed out"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Gagal terhubung ke server."
            admin_facing_error = "Connection timed out"
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "Terjadi kesalahan HTTP.")
                user_facing_error = error_msg_from_api
                admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Respon server tidak valid."
                admin_facing_error = f"HTTP Error {e.response.status_code} with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)
        
        logging.error(f"Batch purchase KMSP failed for user {user_id}, package {package_code}. Full error: {str(e)}")
        logging.error(traceback.format_exc())

                                                                                                  
                                           
        user_data["registered_users"][str(user_id)]["balance"] += required_balance
        
        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": "Pembelian Gagal (Refund)", "package_code": package_code, "package_name": package_name, "phone": phone,
            "amount": required_balance, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "status": "Gagal",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()
        await context.bot.send_message(ADMIN_ID, f"BATCH-BUY: ❌ User {user_id} GAGAL beli {package_name} utk {phone} (LOGIN). Error: {admin_facing_error}", parse_mode="Markdown")
        return {"success": False, "package_name": package_name, "error_message": user_facing_error, "refunded_amount": required_balance, "deeplink": None}


async def process_hesda_package_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = context.user_data.get('phone_for_hesda_batch')
    packages_to_process = context.user_data.get('packages_to_process_hesda_batch', [])
    current_index = context.user_data.get('current_batch_index_hesda', 0)
    total_hesdapkg_batch_price = context.user_data.get('total_hesdapkg_batch_price', 0)                                        

    status_message_id = context.user_data.get('hesda_batch_status_message_id')

    if not packages_to_process or current_index >= len(packages_to_process):
        if status_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan status akhir {status_message_id}: {e}")
        context.user_data.pop('hesda_batch_status_message_id', None)

                                         
        final_summary_parts = ["🏁 *PAKET YANG BERHASIL DI BYPASS* 🏁"]
        success_count = 0
        total_refunded_in_batch = 0

                                                                                              
        for res in context.user_data.get('current_hesda_batch_results', []):
            status_emoji = "✅" if res['success'] else "❌"
            final_summary_parts.append(f"{status_emoji} *{res['package_name']}*: {res.get('status_message', 'Selesai')}")
            if res['success']:
                success_count += 1
            else:
                if res['refunded_amount'] > 0:
                    final_summary_parts.append(f"   (Saldo Rp{res['refunded_amount']:,} dikembalikan)")
                    total_refunded_in_batch += res['refunded_amount']

                                                                                                                
        final_summary_parts.append(f"\n*Total Paket Berhasil*: {success_count} dari {len(packages_to_process)}")
        final_summary_parts.append(f"*Total Saldo Dikembalikan*: Rp{total_refunded_in_batch:,}")
        final_summary_parts.append(f"*Saldo Bot Anda Sekarang*: Rp{user_data['registered_users'][str(user_id)].get('balance', 0):,}")

        await context.bot.send_message(user_id, "\n".join(final_summary_parts), parse_mode="Markdown")
        await send_bypass_menu(update, context)

                                              
        context.user_data.pop('phone_for_hesda_batch', None)
        context.user_data.pop('packages_to_process_hesda_batch', None)
        context.user_data.pop('current_batch_index_hesda', None)
        context.user_data.pop('current_hesda_batch_results', None)
        context.user_data.pop('total_hesdapkg_batch_price', None)                    
        user_data[str(user_id)]["selected_hesdapkg_ids"] = []                                      
        simpan_data_ke_db()
        return

    current_package_id = packages_to_process[current_index]
    package_info = next((p for p in HESDA_PACKAGES if p["id"] == current_package_id), None)

    if not package_info:
        logging.error(f"Paket BYPAS dengan ID {current_package_id} tidak ditemukan dalam daftar HESDA_PACKAGES.")
        message_text = f"❌ Terjadi kesalahan: Paket tidak dikenali ({current_package_id}). Melanjutkan ke paket berikutnya jika ada."
        if status_message_id:
            try:
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=message_text, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(user_id, message_text, parse_mode="Markdown")
        else:
            msg = await context.bot.send_message(user_id, message_text, parse_mode="Markdown")
            context.user_data['hesda_batch_status_message_id'] = msg.message_id
        
                                                                                          
        refund_amount_for_this_package = package_info.get('price_bot', 0) if package_info else 0
        user_data["registered_users"][str(user_id)]["balance"] += refund_amount_for_this_package
        simpan_data_ke_db()
        context.user_data['current_hesda_batch_results'].append({
            "success": False, 
            "package_name": package_info.get('name', 'Paket Tidak Dikenali'), 
            "error_message": "Paket tidak ditemukan atau tidak valid.", 
            "refunded_amount": refund_amount_for_this_package,
            "status_message": "Gagal (Paket Tidak Ditemukan)"
        })

        context.user_data['current_batch_index_hesda'] += 1
        asyncio.create_task(process_hesda_package_queue(update, context))
        return

    package_name = package_info['name']
    required_balance_for_this_package = package_info['price_bot']                                      

    processing_text = f"Memproses pembelian: *{package_name}* ({current_index + 1} dari {len(packages_to_process)})"
    if status_message_id:
        try:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=processing_text, parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status {status_message_id} dengan '{processing_text}': {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, processing_text, parse_mode="Markdown")
            context.user_data['hesda_batch_status_message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(user_id, processing_text, parse_mode="Markdown")
        context.user_data['hesda_batch_status_message_id'] = msg.message_id
        status_message_id = msg.message_id

    access_token_hesda = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {}).get(phone, {}).get("hesda", {}).get("access_token")

    if not access_token_hesda:
        logging.info(f"No BYPAS token found for {phone}. Initiating OTP flow for batch purchase.")
                                                              
        context.user_data['pending_hesda_batch_after_otp'] = packages_to_process[current_index:]
        context.user_data['phone_for_hesda_batch'] = phone
        context.user_data['current_login_provider'] = 'hesda'
        context.user_data['next'] = 'handle_login_otp_input'
        context.user_data['resume_hesda_purchase_after_otp'] = True

                                                                                                   
                                                                                         
        user_data["registered_users"][str(user_id)]["balance"] += total_hesdapkg_batch_price - sum(r.get('refunded_amount', 0) for r in context.user_data['current_hesda_batch_results'] if not r['success'])
        simpan_data_ke_db()
        
        await context.bot.send_message(user_id, f"❌ Token BYPAS tidak ditemukan untuk nomor `{phone}`. Silakan login ulang untuk melanjutkan pembelian batch. Saldo Anda akan dikembalikan jika tidak melanjutkan.")

        if status_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception:
                pass
        context.user_data.pop('hesda_batch_status_message_id', None)

        await request_otp_and_prompt_hesda(update, context, phone)
        return

                                                                               
    purchase_result = await execute_single_purchase_hesda(update, context, user_id, current_package_id, package_name, phone, access_token_hesda, "PULSA", required_balance_for_this_package, "menu_bypass_nested")
    
                                                                                                
                                                            
    if not purchase_result['success'] and purchase_result.get('refunded_amount', 0) == 0:
                                                                                                                 
                                                                          
                                                                                            
        pass                                                                                                     

    context.user_data['current_hesda_batch_results'].append(purchase_result)

    result_text = ""
    if purchase_result['success']:
        result_text = f"✅ Paket *{package_name}* berhasil di BYPAS!."
    else:
        result_text = f"❌ Gagal membeli *{package_name}*: `{purchase_result['error_message']}`."
        if purchase_result['refunded_amount'] > 0:
            result_text += f" Saldo Rp{purchase_result['refunded_amount']:,} telah dikembalikan."

    if status_message_id:
        try:
            await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=result_text, parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Gagal mengedit pesan status {status_message_id} dengan hasil: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, result_text, parse_mode="Markdown")
            context.user_data['hesda_batch_status_message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(user_id, result_text, parse_mode="Markdown")
        context.user_data['hesda_batch_status_message_id'] = msg.message_id
        status_message_id = msg.message_id


    context.user_data['current_batch_index_hesda'] += 1
    
    if context.user_data.get('current_batch_index_hesda') < len(packages_to_process):
        pause_text = "⏸️ Jeda 10 detik sebelum memproses paket berikutnya menghindari error..."
        if status_message_id:
            try:
                await context.bot.edit_message_text(chat_id=user_id, message_id=status_message_id, text=pause_text, parse_mode="Markdown")
            except Exception as e:
                logging.warning(f"Gagal mengedit pesan status {status_message_id} dengan jeda: {e}. Mengirim pesan baru.")
                msg = await context.bot.send_message(user_id, pause_text, parse_mode="Markdown")
                context.user_data['hesda_batch_status_message_id'] = msg.message_id
        else:
            msg = await context.bot.send_message(user_id, pause_text, parse_mode="Markdown")
            context.user_data['hesda_batch_status_message_id'] = msg.message_id
            
        await asyncio.sleep(10)
        asyncio.create_task(process_hesda_package_queue(update, context))
    else:
                                                     
                                                                                    
        await process_hesda_package_queue(update, context)                             
        if status_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan status terakhir {status_message_id} sebelum ringkasan: {e}")
        context.user_data.pop('hesda_batch_status_message_id', None)                     

        final_summary_parts = ["🏁 *PAKET YANG BERHASIL BYPASS * 🏁"]
        for res in context.user_data['current_hesda_batch_results']:
            status_emoji = "✅" if res['success'] else "❌"
            final_summary_parts.append(f"{status_emoji} *{res['package_name']}*: {res.get('status_message', 'Selesai')}")
            if not res['success'] and res['refunded_amount'] > 0:
                final_summary_parts.append(f"   (Saldo Rp{res['refunded_amount']:,} dikembalikan)")
        
        await context.bot.send_message(user_id, "\n".join(final_summary_parts), parse_mode="Markdown")
        await send_bypass_menu(update, context)
                                              
        context.user_data.pop('phone_for_hesda_batch', None)
        context.user_data.pop('packages_to_process_hesda_batch', None)
        context.user_data.pop('current_batch_index_hesda', None)
        context.user_data.pop('current_hesda_batch_results', None)
        user_data[str(user_id)]["selected_hesdapkg_ids"] = []                                  
        simpan_data_ke_db()

async def process_30h_package_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = context.user_data.get('phone_for_30h_batch')
    packages_to_process = context.user_data.get('packages_to_process_30h_batch', [])
    current_index = context.user_data.get('current_batch_index_30h', 0)
    total_30h_batch_price = context.user_data.get('total_30h_batch_price', 0) 

    status_message_id = context.user_data.get('30h_batch_status_message_id')

                                        
                                                 
    access_token_kmsp = context.user_data.get('token_for_30h_batch')
                                        

    if status_message_id is None:
        initial_status_text = f"⏳ Memulai pembelian batch 30H untuk {phone}...\nMemproses paket 1 dari {len(packages_to_process)}. Mohon tunggu."
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan callback query {update.callback_query.message.message_id}: {e}")
        
        msg = await context.bot.send_message(user_id, initial_status_text, parse_mode="Markdown")
        context.user_data['30h_batch_status_message_id'] = msg.message_id
        status_message_id = msg.message_id
    
    if not packages_to_process or current_index >= len(packages_to_process):
        if status_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception as e:
                logging.warning(f"Gagal menghapus pesan status akhir {status_message_id} untuk 30H: {e}")
        context.user_data.pop('30h_batch_status_message_id', None)
        
                                                       
        context.user_data.pop('token_for_30h_batch', None)

        final_summary_parts = ["🏁 *RINGKASAN PEMBELIAN PAKET 30H* 🏁"]
        success_count = 0
        total_refunded_in_batch = 0

        for res in context.user_data.get('current_30h_batch_results', []):
            status_emoji = "✅" if res['success'] else "❌"
            escaped_package_name = escape_markdown(res['package_name'], version=2)
            escaped_status_message = escape_markdown(res.get('status_message', 'Selesai'), version=2)
            final_summary_parts.append(f"{status_emoji} *{escaped_package_name}*: {escaped_status_message}")
            if not res['success'] and res['refunded_amount'] > 0:
                final_summary_parts.append(f"   (Saldo Rp{res['refunded_amount']:,} dikembalikan)")
            if res['success']:                       
                success_count += 1
            if not res['success']:                      
                total_refunded_in_batch += res.get('refunded_amount', 0)


        final_summary_parts.append(f"\n*Total Paket Berhasil*: {success_count} dari {len(packages_to_process)}")
        final_summary_parts.append(f"*Total Saldo Dikembalikan*: Rp{total_refunded_in_batch:,}")
        final_summary_parts.append(f"*Saldo Bot Anda Sekarang*: Rp{user_data['registered_users'][str(user_id)].get('balance', 0):,}")

        try:
            await context.bot.send_message(user_id, "\n".join(final_summary_parts), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send final summary message to user {user_id}: {e}", exc_info=True)
            await context.bot.send_message(user_id, "Terjadi kesalahan saat menampilkan ringkasan pembelian. Silakan cek riwayat transaksi Anda.")
        
        await send_30h_menu(update, context) 

        context.user_data.pop('phone_for_30h_batch', None)
        context.user_data.pop('packages_to_process_30h_batch', None)
        context.user_data.pop('current_batch_index_30h', None)
        context.user_data.pop('current_30h_batch_results', None)
        context.user_data.pop('total_30h_batch_price', None)
        user_data["registered_users"][str(user_id)]["selected_30h_pkg_ids"] = [] 
        simpan_data_ke_db()
        return

    current_package_id = packages_to_process[current_index]
    package_info = next((p for p in THIRTY_H_PACKAGES if p["id"] == current_package_id), None)

    if not package_info:
        logging.error(f"Paket 30H dengan ID {current_package_id} tidak ditemukan dalam daftar THIRTY_H_PACKAGES. Melewatkan paket ini.")
        message_text = f"❌ Terjadi kesalahan: Paket tidak dikenali (`{escape_markdown(current_package_id, version=2)}`). Melanjutkan ke paket berikutnya jika ada."
        
        await context.bot.send_message(user_id, message_text, parse_mode="Markdown")
        
        refund_amount_for_this_package = package_info.get('price_bot', 0) if package_info else 0
        if refund_amount_for_this_package > 0:
            user_data["registered_users"][str(user_id)]["balance"] += refund_amount_for_this_package
            simpan_data_ke_db()
        context.user_data.setdefault('current_30h_batch_results', []).append({
            "success": False, 
            "package_name": package_info.get('name', 'Paket Tidak Dikenali'), 
            "error_message": "Paket tidak ditemukan atau tidak valid.", 
            "refunded_amount": refund_amount_for_this_package,
            "status_message": "Gagal (Paket Tidak Ditemukan)"
        })

        context.user_data['current_batch_index_30h'] += 1
        asyncio.create_task(process_30h_package_queue(update, context))
        return

    package_name = package_info['name']
    required_balance_for_this_package = package_info['price_bot'] 

    escaped_package_name_in_progress = escape_markdown(package_name, version=2)
    progress_message_content = f"⏳ Sedang memproses paket *{escaped_package_name_in_progress}* ({current_index + 1} dari {len(packages_to_process)}) untuk nomor {phone}..."
    try:
        await context.bot.edit_message_text(
            chat_id=user_id, 
            message_id=status_message_id, 
            text=progress_message_content, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏹️ Hentikan Proses", callback_data="stop_batch_purchase")]])
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logging.warning(f"Gagal mengedit pesan status {status_message_id} dengan progres untuk 30H: {e}. Mengirim pesan baru.")
            msg = await context.bot.send_message(user_id, progress_message_content, parse_mode="Markdown")
            context.user_data['30h_batch_status_message_id'] = msg.message_id
            status_message_id = msg.message_id 

                                        
                                                                            
                                                                                                                                                            
                                        

    if not access_token_kmsp:
        logging.info(f"No KMSP token found for {phone}. Initiating OTP flow for 30H batch purchase.")                                       
        context.user_data['pending_30h_batch_after_otp'] = packages_to_process[current_index:]
        context.user_data['phone_for_30h_batch'] = phone
        context.user_data['current_login_provider'] = 'kmsp' 
        context.user_data['next'] = 'handle_login_otp_input'
        context.user_data['resume_30h_purchase_after_otp'] = True 

                                                                 
        processed_packages_price = sum(
            res.get('deducted_balance', 0) - res.get('refunded_amount', 0) 
            for res in context.user_data.get('current_30h_batch_results', [])
        )
        sisa_saldo_refund = total_30h_batch_price - processed_packages_price
        if sisa_saldo_refund > 0:
            user_data["registered_users"][str(user_id)]["balance"] += sisa_saldo_refund
            simpan_data_ke_db()
        
        await context.bot.send_message(user_id, f"❌ Token LOGIN tidak ditemukan untuk nomor `{phone}`. Silakan login ulang untuk melanjutkan pembelian batch 30H. Saldo yang belum terpakai (Rp{sisa_saldo_refund:,}) telah dikembalikan sementara.", parse_mode="Markdown")

        if status_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception:
                pass
        context.user_data.pop('30h_batch_status_message_id', None)

        await request_otp_and_prompt_kmsp(update, context, phone)
        return

    purchase_result = await execute_single_purchase_30h( 
        update, context, user_id, current_package_id, package_name, phone, access_token_kmsp, 
        "BALANCE", required_balance_for_this_package, "menu_30h_nested" 
    )
    
    context.user_data.setdefault('current_30h_batch_results', []).append(purchase_result)

    context.user_data['current_batch_index_30h'] += 1
    
    if context.user_data.get('current_batch_index_30h') < len(packages_to_process):
        pause_text_duration = 10
        await asyncio.sleep(pause_text_duration) 

        asyncio.create_task(process_30h_package_queue(update, context))
    else:
        await process_30h_package_queue(update, context)

async def execute_single_purchase(update, context, user_id, package_code, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, provider="kmsp", attempt=1, package_name_for_display=None):
    url = ""
    package_name_display = package_name_for_display if package_name_for_display else ""

    api_price_or_fee = 0

    if package_code == XC1PLUS1GB_DANA_CODE:
        api_price_or_fee = 2500
    elif package_code == XC1PLUS1GB_PULSA_CODE:
        api_price_or_fee = 2500
    elif package_code == "XLUNLITURBOVIDIO_DANA":
        api_price_or_fee = 1500
    elif package_code == XUTS_PACKAGE_CODE:
        api_price_or_fee = 0
    else:
        all_api_packages = context.user_data.get('all_api_packages', [])
        found_api_package_info = next((p for p in all_api_packages if p.get("package_code") == package_code), None)
        if found_api_package_info:
            api_harga_str = found_api_package_info.get("package_harga", "Rp. 0,00")
            cleaned_harga_str = api_harga_str.replace("Rp. ", "").replace(".", "").replace(",", "")
            try:
                api_price_or_fee = int(float(cleaned_harga_str))
            except ValueError:
                api_price_or_fee = 0
        else:
            api_price_or_fee = 0

    if provider == "kmsp":
        url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={package_code}&phone={phone}&access_token={access_token}&payment_method={payment_method}&price_or_fee={api_price_or_fee}"
        
        if not package_name_for_display:
            if return_menu_callback_data == 'xcp_addon_dana':
                package_info = next((p for p in ADD_ON_SEQUENCE if p["code"] == package_code), None)
                package_name_display = package_info['name'] if package_info else package_code
            elif return_menu_callback_data == 'xcp_addon':
                package_name_display = XCP_8GB_PACKAGE['name'] if package_code == XCP_8GB_PACKAGE['code'] else package_code
                if package_code == "c03be70fb3523ac2ac440966d3a5920e_QRIS":
                    package_name_display = XCP_8GB_PACKAGE['name'] + " QRIS"
            elif return_menu_callback_data == 'menu_uts_nested':
                if package_code == "XLUNLITURBOSUPERXC_PULSA":
                    package_name_display = "XUTS"
                elif package_code == "XL_XC1PLUS1DISC_EWALLET":
                    package_name_display = "XC 1+1GB DANA"
                elif package_code == "XL_XC1PLUS1DISC_PULSA":
                    package_name_display = "XC 1+1GB PULSA"
                elif package_code == "XL_XC1PLUS1DISC_QRIS":
                    package_name_display = "XC 1+1GB QRIS"
                else:
                    package_name_display = package_code
            elif return_menu_callback_data == 'vidio_xl_menu':
                pass
            else:
                package_name_display = package_code
    else:
        await context.bot.send_message(user_id, "Terjadi kesalahan internal. Provider API tidak dikenali.", parse_mode="Markdown")
        if deducted_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            simpan_data_ke_db()
        return

    status_msg = await context.bot.send_message(user_id, f"Memproses pembelian *{package_name_display}* dari LOGIN...\nProses ini dapat memakan waktu hingga 60 detik. Harap tunggu.", parse_mode="Markdown")
    loop = asyncio.get_running_loop()

    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    try:
        def blocking_api_call():
            return requests.get(url, timeout=58)

        response = await asyncio.wait_for(
            loop.run_in_executor(None, blocking_api_call),
            timeout=60.0
        )

        try:
            await status_msg.delete()
        except Exception as e:
            logging.warning(f"Gagal menghapus pesan status setelah panggilan API KMSP: {e}")

        response.raise_for_status()
        result = response.json()

        if isinstance(result, list): result = result[0] if result else {}

        api_message = result.get('message', '')
        api_status = result.get('status', False)
        api_code = result.get('code', '')

        if package_code == "XLUNLITURBOSUPERXC_PULSA":
            SUCCESS_422_MESSAGE = "Error Message: 422 -> Failed call ipaas purchase, with status code:422 : null"
            if SUCCESS_422_MESSAGE in api_message:
                logging.info(f"Pembelian XUTS PULSA untuk {phone} dianggap SUKSES karena respons 422 spesifik: '{api_message}'")
                text = (
                    f"✅ *NOMOR KAMU SUPORT XUTS* ✅\n"
                    f"Silakan cek SMS pastikan ada SMS \"maaf transaksi anda tidak dapat di proses\" atau SMS gagal lainya silahkan lanjutkan untuk membeli paket XC 1+1GB"
                )
                keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu UTS", callback_data="menu_uts_nested")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)

                user_data["registered_users"][str(user_id)]["transactions"].append({
                    "type": f"Pembelian Paket (LOGIN - XUTS Sukses 422)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                    "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil (422)",
                    "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
                })
                simpan_data_ke_db()

                user_info = user_data["registered_users"][str(user_id)]
                user_first_name = user_info.get("first_name", "N/A")
                user_username = user_info.get("username", "N/A")
                remaining_balance = user_info.get("balance", 0)

                admin_message = (
                    f"✅ *PEMBELIAN XUTS BERHASIL (LOGIN - Khusus 422)!* ✅\n"
                    f"User ID: `{user_id}`\n"
                    f" (`{escape_markdown(user_first_name, version=2)}` / `@{escape_markdown(user_username, version=2)}`)\n"
                    f"Nomor HP: `{phone}`\n"
                    f"Kode Paket: `{package_code}`\n"
                    f" ({escape_markdown(package_name_display, version=2)})\n"
                    f"Metode Pembayaran: `{payment_method}`\n"
                    f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
                    f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
                    f"Waktu Transaksi: `{transaction_time_str}`"
                )
                await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
                return
            else:
                logging.info(f"Pembelian XUTS PULSA untuk {phone} dianggap GAGAL meskipun status API: {api_status}, pesan: '{api_message}'. Memaksa error.")
                
                if deducted_balance > 0:
                    user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
                    user_data["registered_users"][str(user_id)]["transactions"].append({
                        "type": f"Pembelian Gagal (LOGIN - XUTS Refund)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                        "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal (Refund)",
                        "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
                    })
                    simpan_data_ke_db()
                    
                    user_info = user_data["registered_users"][str(user_id)]
                    user_first_name = user_info.get("first_name", "N/A")
                    user_username = user_info.get("username", "N/A")
                    remaining_balance = user_info.get("balance", 0)
                    
                    user_message = (
                        "*PROSES BERHASIL *✅\n\n"
                        "TUNGGU 10 MENIT,Coba Beli ulang lagi paket nya setelah 10 menit"
                    )
                    keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu UTS", callback_data="menu_uts_nested")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(user_id, user_message, parse_mode="Markdown", reply_markup=reply_markup)

                    admin_message = (f"❌ *PEMBELIAN XUTS GAGAL !* ❌\n"
                                     f"User ID: `{user_id}`\n"
                                     f" (`{escape_markdown(user_first_name, version=2)}` / `@{escape_markdown(user_username, version=2)}`)\n"
                                     f"Nomor HP: `{phone}`\n"
                                     f"Kode Paket: `{package_code}`\n"
                                     f" ({escape_markdown(package_name_display, version=2)})\n"
                                     f"Metode Pembayaran: `{payment_method}`\n"
                                     f"Saldo Dikembalikan: `Rp{deducted_balance:,}`\n"
                                     f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
                                     f"Waktu Transaksi: `{transaction_time_str}`\n"
                                     f"Pesan API: `{escape_markdown(api_message, version=2)}`")
                    await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
                return
        
        if not api_status:
            raise ValueError(api_message or f'API LOGIN mengembalikan status false untuk {package_code}')

        data = result.get("data", {})

        is_qris = data.get("is_qris", False)
        qris_image_url = None

        if is_qris and payment_method == "QRIS":
            qris_data = data.get("qris_data", {})
            qris_code_raw_string = qris_data.get("qr_code")
            remaining_time = qris_data.get("remaining_time")

            if not qris_code_raw_string or not remaining_time:
                raise ValueError("Data QRIS dari API tidak lengkap.")

            qris_image_url = f"https://quickchart.io/qr?text={qris_code_raw_string}&size=300"
            escaped_package_name_display = escape_markdown(package_name_display, version=2)

            pesan_info_qris = (
                f"Silakan scan QRIS untuk membayar *{escaped_package_name_display}*.\n\n"
                f"Setelah berhasil membayar, tekan tombol *'✅ Sudah Bayar'* di bawah.\n\n"
                f"⚠️ QRIS ini akan kedaluwarsa dalam *{remaining_time} detik*."
            )
            keyboard = [[InlineKeyboardButton("✅ Sudah Bayar", callback_data="qris_paid_manual_confirm")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            qris_photo_msg = await context.bot.send_photo(chat_id=user_id, photo=qris_image_url)
            qris_text_msg = await context.bot.send_message(user_id, pesan_info_qris, parse_mode="Markdown", reply_markup=reply_markup)

            context.user_data['active_qris_messages'] = {
                'photo': qris_photo_msg.message_id,
                'text': qris_text_msg.message_id
            }

            context.job_queue.run_once(
                qris_expiration_job,
                remaining_time,
                data={'user_id': user_id, 'qris_message_id': qris_text_msg.message_id, 'qris_photo_id': qris_photo_msg.message_id},
                name=f"qris_expiration_single_{user_id}_{qris_text_msg.message_id}"
            )

        else:
            deeplink_url = data.get("deeplink_data", {}).get("deeplink_url")
            have_deeplink = data.get("have_deeplink", False)

            escaped_package_name_display = escape_markdown(package_name_display, version=2)
            text = f"🎉 *Pembelian {escaped_package_name_display} dari LOGIN Berhasil Diproses!*"

            keyboard = []
            if payment_method == "BALANCE":
                text += "\nPaket telah berhasil diaktifkan di nomormu. Silakan cek kuota."
            elif have_deeplink and deeplink_url:
                text += "\nSilakan lanjutkan pembayaran melalui link di bawah ini."
                keyboard.append([InlineKeyboardButton("💰 BAYAR SEKARANG", url=deeplink_url)])
            else:
                text += "\nPaket telah berhasil diaktifkan di nomormu. Silakan cek kuota."


            if return_menu_callback_data == 'xcp_addon_dana':
                keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu DANA", callback_data="xcp_addon_dana")])
            elif return_menu_callback_data == 'xcp_addon':
                keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu XCS ADD ON", callback_data="xcp_addon")])
            elif return_menu_callback_data == 'menu_uts_nested':
                keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu UTS", callback_data="menu_uts_nested")])
            elif return_menu_callback_data == 'vidio_xl_menu':
                keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu VIDIO XL", callback_data="vidio_xl_menu")])
            elif return_menu_callback_data == 'iflix_xl_menu': 
                keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu IFLIX XL", callback_data="iflix_xl_menu")])
            else:
                keyboard.append([InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)

        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": f"Pembelian Paket (LOGIN)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
            "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()

        user_info = user_data["registered_users"][str(user_id)]
        user_first_name = user_info.get("first_name", "N/A")
        user_username = user_info.get("username", "N/A")
        remaining_balance = user_info.get("balance", 0)

        escaped_package_name_display_admin = escape_markdown(package_name_display, version=2)
        admin_message = (
            f"✅ *PEMBELIAN BERHASIL (LOGIN)!* ✅\n"
            f"User ID: `{user_id}`\n"
            f" (`{escape_markdown(user_first_name, version=2)}` / `@{escape_markdown(user_username, version=2)}`)\n"
            f"Nomor HP: `{phone}`\n"
            f"Kode Paket: `{package_code}`\n"
            f" ({escaped_package_name_display_admin})\n"
            f"Metode Pembayaran: `{payment_method}`\n"
            f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
            f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
            f"Waktu Transaksi: `{transaction_time_str}`"
        )
        if is_qris and qris_image_url:
            admin_message += f"\nQRIS Image URL: {qris_image_url}"

        admin_keyboard = None
        if not is_qris and data.get("have_deeplink", False) and data.get("deeplink_data", {}).get("deeplink_url"):
            admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Link Pembayaran User", url=data.get("deeplink_data", {}).get("deeplink_url"))]])

        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown", reply_markup=admin_keyboard)

                                                    
    except Exception as e:
        try:
            await status_msg.delete()
        except Exception:
            pass

        error_type = type(e).__name__
        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)

                                                         
        TOKEN_EXPIRED_MESSAGE = "Terjadi kesalahan saat menampilkan data subscriber info!"
        is_token_error = False
        
                                                                               
        if isinstance(e, ValueError) and TOKEN_EXPIRED_MESSAGE in str(e):
            is_token_error = True
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "")
                if TOKEN_EXPIRED_MESSAGE in error_msg_from_api:
                    is_token_error = True
                    admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                pass
        
        if is_token_error:
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUWARSA* ⚠️\n"
                "Kemungkinan saat maintenance XL merefresh token login. Coba login ulang."
            )
                                   
        
        elif isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
            admin_facing_error = "Request timed out after 60 seconds"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Tidak dapat terhubung ke server (Connection Timeout)."
            admin_facing_error = "Connection timed out"
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                                                                
                error_msg_from_api = e.response.json().get("message", "Terjadi kesalahan HTTP.")
                user_facing_error = f"Pesan dari API: {error_msg_from_api}"
                admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respons yang tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)
            
        escaped_package_name_display = escape_markdown(package_name_display, version=2)
        escaped_user_facing_error = escape_markdown(user_facing_error, version=2)
        escaped_admin_facing_error = escape_markdown(admin_facing_error, version=2)

        final_user_error_message = f"❌ Gagal melakukan pembelian *{escaped_package_name_display}* dari LOGIN.\n*Pesan Error:*\n`{escaped_user_facing_error}`"

        if deducted_balance > 0:
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Gagal (LOGIN) (Refund)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            final_user_error_message += f"\n💰 Saldo Anda sebesar *Rp{deducted_balance:,}* telah dikembalikan."

        retry_data_key = uuid.uuid4().hex[:10]
        context.bot_data[f"retry_data_{retry_data_key}"] = json.dumps({
            'provider': provider,
            'package_id_or_code': package_code,
            'package_name': package_name_display,
            'phone': phone,
            'payment_method': payment_method,
            'deducted_balance': deducted_balance,
            'return_menu_callback_data': return_menu_callback_data,
            'package_name_for_display': package_name_display
        }).encode('utf-8').decode('utf-8')

        callback_data_retry = f"retry_single_{retry_data_key}"

        retry_keyboard = [[InlineKeyboardButton("🔁 COBA BELI LAGI", callback_data=callback_data_retry)]]
        reply_markup = InlineKeyboardMarkup(retry_keyboard)

        await context.bot.send_message(user_id, final_user_error_message, parse_mode="Markdown", reply_markup=reply_markup)

        admin_message = (f"❌ *PEMBELIAN GAGAL (LOGIN)!* ❌\n"
                         f"User ID: `{user_id}`\nNomor HP: `{phone}`\nKode Paket: `{package_code}`\n"
                         f"Metode Pembayaran: `{payment_method}`\n"
                         f"Error: `{error_type}` - `{escaped_admin_facing_error}` (Saldo direfund)")
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

async def execute_single_purchase_hesda(update, context, user_id, package_id, package_name, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt=1):
    url = "https://api.hesda-store.com/v2/beli/otp"
    headers = get_hesda_auth_headers()
    if not headers:
        return {"success": False, "package_name": package_name, "error_message": "Informasi otentikasi tidak lengkap. Hubungi admin.", "refunded_amount": deducted_balance, "status_message": "Gagal (Auth Error)"}

    payload = {
        "hesdastore": HESDA_API_KEY,
        "package_id": package_id,
        "access_token": access_token,
        "uri": "package_purchase_otp",
        "no_hp": phone,
        "payment_method": payment_method,
        "url_callback": "YOUR_OPTIONAL_CALLBACK_URL" 
    }
    
    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    raw_api_response = {}

    try:
        def blocking_api_call():
            return requests.post(url, headers=headers, data=payload, timeout=58)

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(None, blocking_api_call),
            timeout=60.0 
        )
        
        raw_api_response = response.json()

                                                                      
        if response.status_code == 422:
            error_message_from_api = raw_api_response.get('message', '')
            if "Error Message: 422 -> Failed call ipaas purchase, with status code:422 : null" in error_message_from_api:
                logging.info(f"Pembelian BYPAS untuk {package_name} di {phone} dianggap SUKSES meskipun respons API 422 dengan pesan tertentu. (Percobaan {attempt})")
                result = raw_api_response
            else:
                response.raise_for_status() 
                result = raw_api_response
        else:
            response.raise_for_status() 
            result = raw_api_response

        if isinstance(result, list): result = result[0] if result else {}
        
        if not result.get('status', True) and not ("Error Message: 422 -> Failed call ipaas purchase, with status code:422 : null" in result.get('message', '')):
            raise ValueError(result.get('message', 'API BYPAS mengembalikan status gagal atau respons tidak jelas.'))

                                                                      
                                                                     
                                                      

        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": "Pembelian Paket (BYPAS)", "package_id": package_id, "package_name": package_name, "phone": phone,
            "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()
        
        user_info = user_data["registered_users"][str(user_id)]
        user_first_name = user_info.get("first_name", "N/A")
        user_username = user_info.get("username", "N/A")
        remaining_balance = user_info.get("balance", 0)                                             

        admin_message = (
            f"✅ *BYPAS BERHASIL!* ✅\n"
            f"User ID: `{user_id}`\n"
            f" (`{user_first_name}` / `@{user_username}`)\n"
            f"Nomor HP: `{phone}`\n"
            f"ID Paket: `{package_id}`\n"
            f"Nama Paket: `{package_name}`\n" 
            f"Saldo Diproses: `Rp{deducted_balance:,}`\n"                                      
            f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
            f"Waktu Transaksi: `{transaction_time_str}`"
        )
        
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
        
        return {"success": True, "package_name": package_name, "error_message": None, "refunded_amount": 0, "status_message": "Berhasil"}

    except Exception as e:
        error_type = type(e).__name__
        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)
        
                                                         
        TOKEN_EXPIRED_MESSAGE = "Terjadi kesalahan saat menampilkan data subscriber info!"
        is_token_error = False

        if isinstance(e, ValueError) and TOKEN_EXPIRED_MESSAGE in str(e):
            is_token_error = True
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "")
                if TOKEN_EXPIRED_MESSAGE in error_msg_from_api:
                    is_token_error = True
                    admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                pass
                                   

        if isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Waktu tunggu habis. Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
            admin_facing_error = "Request timed out after 60 seconds (Hesda API)"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Gagal terhubung. Tidak dapat terhubung ke server (Connection Timeout)."
            admin_facing_error = "Connection timed out (Hesda API)"
        elif isinstance(e, requests.exceptions.HTTPError) and not is_token_error:
            try:
                response_json = e.response.json()
                user_facing_error = f"Pesan dari server: {response_json.get('message', 'Terjadi kesalahan HTTP.')}"
                admin_facing_error = f"HTTP Error {e.response.status_code} (Hesda API): {response_json.get('message', 'No message')}"
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respons tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} (Hesda API) with non-JSON response."
        elif isinstance(e, ValueError) and not is_token_error:
            user_facing_error = str(e)
            admin_facing_error = str(e)
        
        logging.error(f"Pembelian Hesda gagal untuk user {user_id}, paket {package_id}. Error: {str(e)}")
        logging.error(traceback.format_exc())

        MAX_RETRIES = 3
        RETRY_DELAY = 10

                                                 
        is_general_token_error = "access token is invalid" in admin_facing_error.lower() or \
                                 "token invalid" in admin_facing_error.lower() or \
                                 "token expired" in admin_facing_error.lower() or \
                                 "gagal login" in admin_facing_error.lower()

                                                                    
        if is_token_error:
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUARSA* ⚠️\n"
                "Kemungkinan saat maintenance XL merefresh token login. Coba login ulang."
            )

                                                                                      
        if attempt < MAX_RETRIES and not is_token_error and not is_general_token_error:
            logging.info(f"Mencoba lagi pembelian BYPAS untuk {package_name} (percobaan {attempt + 1})... Menunda {RETRY_DELAY} detik.")
            await asyncio.sleep(RETRY_DELAY)
            return await execute_single_purchase_hesda(update, context, user_id, package_id, package_name, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt + 1)
        else:
                                                                                        
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": "Pembelian Gagal (BYPAS) (Refund)", "package_id": package_id, "package_name": package_name, "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal (Refund)",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            logging.info(f"Saldo user {user_id} dikembalikan {deducted_balance} karena kegagalan pembelian BYPAS (maksimal percobaan atau error token).")
        
            admin_message = (f"❌ *PEMBELIAN GAGAL (BYPAS)!* ❌\n"
                             f"User ID: `{user_id}`\nNomor HP: `{phone}`\nID Paket: `{package_id}`\n"
                             f"({package_name})\n"
                             f"Error: `{error_type}` - `{admin_facing_error}` (Saldo direfund)\n"
                             f"Total Percobaan: `{attempt}`")
                                                           
            unique_key = uuid.uuid4().hex
            context.bot_data[f" Bethesda_API_Response_Data_{unique_key}"] = json.dumps(raw_api_response, indent=2)
            admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📄 Lihat Respon API", callback_data=f" Bethesda_api_res_{unique_key}")]])
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown", reply_markup=admin_keyboard)

            return {"success": False, "package_name": package_name, "error_message": user_facing_error, "refunded_amount": deducted_balance, "status_message": "Gagal"}

async def execute_single_purchase_30h(update, context, user_id, package_code, package_name_display, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt=1):
    url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={package_code}&phone={phone}&access_token={access_token}&payment_method={payment_method}&price_or_fee=0"
    
    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    raw_api_response_content = None 
    
    try:
        def blocking_api_call():
            return requests.get(url, timeout=58)

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(None, blocking_api_call),
            timeout=60.0 
        )
        
        raw_api_response_content = response.text 
        
        result = {}
        api_message = ""
        api_status = False 

        try:
            parsed_json = response.json()
            if isinstance(parsed_json, list):
                result = parsed_json[0] if parsed_json else {}
            else:
                result = parsed_json
            
            api_message = result.get('message', '').strip().replace('\r', '').replace('\n', '')
            api_status = result.get('status', False) 
        except json.JSONDecodeError:
            logging.warning(f"Failed to decode JSON from 30H API response: {raw_api_response_content[:200]}...")
            api_message = f"Invalid JSON response or non-JSON content: {raw_api_response_content[:100]}...".strip().replace('\r', '').replace('\n', '')
            api_status = False 

        EXPECTED_SUCCESS_MESSAGE_CONTAINING_422 = "Error Message: 422 -> Failed call ipaas purchase, with status code:422 : null,".strip().replace('\r', '').replace('\n', '')
        EXPECTED_PENDING_MESSAGE_MYXL = "Paket berhasil dibeli. Silakan cek kuotanya via aplikasi MyXL (disarankan) dan/atau via SMS kamu".strip().replace('\r', '').replace('\n', '')


        if response.status_code == 200 and EXPECTED_SUCCESS_MESSAGE_CONTAINING_422 in api_message:
            logging.info(f"Pembelian 30H (KMSP) untuk {phone} ({package_name_display}) dianggap SUKSES karena respons HTTP 200 dengan pesan 422 spesifik. (Percobaan {attempt})")
            
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Paket (LOGIN - 30H Sukses 200_dengan_422_message)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil (200_dengan_422_message)",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()

            user_info = user_data["registered_users"][str(user_id)]
            user_first_name = user_info.get("first_name", "N/A")
            user_username = user_info.get("username", "N/A")
            remaining_balance = user_info.get("balance", 0)

            admin_message = (
                f"✅ *PEMBELIAN 30H BERHASIL (LOGIN - Khusus 200 dengan Pesan 422)!* ✅\n"
                f"User ID: `{user_id}`\n"
                f" (`{escape_markdown(user_first_name, version=2)}` / `@{escape_markdown(user_username, version=2)}`)\n"
                f"Nomor HP: `{phone}`\n"
                f"Kode Paket: `{package_code}`\n"
                f" ({escape_markdown(package_name_display, version=2)})\n"
                f"Metode Pembayaran: `{payment_method}`\n"
                f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
                f"Sisa Saldo: `Rp{remaining_balance:,}`\n"
                f"Waktu Transaksi: `{transaction_time_str}`"
            )
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
            
            return {"success": True, "package_name": package_name_display, "error_message": None, "refunded_amount": 0, "status_message": "Berhasil (200_dengan_422_message)"}
        
        elif response.status_code == 200 and EXPECTED_PENDING_MESSAGE_MYXL in api_message:
            logging.info(f"Pembelian 30H (KMSP) untuk {phone} ({package_name_display}) dianggap PENDING karena respon 200 dgn pesan MyXL, perlu jeda & retry. (Percobaan {attempt})")
            
                                                          
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Paket (LOGIN - 30H Pending Retry) (Refund)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Pending (Refund)", 
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            logging.info(f"Saldo user {user_id} dikembalikan Rp{deducted_balance} karena 30H pending (MyXL message).")

            user_info = user_data["registered_users"][str(user_id)]
            admin_message = (
                f"⚠️ *PEMBELIAN 30H PENDING (LOGIN)!* ⚠️\n"
                f"User ID: `{user_id}` (`{escape_markdown(user_info.get('first_name', 'N/A'), version=2)}` / `@{escape_markdown(user_info.get('username', 'N/A'), version=2)}`)\n"
                f"Nomor HP: `{phone}`\n"
                f"Kode Paket: `{package_code}`\n"
                f" ({escape_markdown(package_name_display, version=2)})\n"
                f"Metode Pembayaran: `{payment_method}`\n"
                f"Saldo Dipotong Awal: `Rp{deducted_balance:,}` (SUDAH DIREFUND)\n"
                f"Sisa Saldo: `Rp{user_info.get('balance', 0):,}`\n"
                f"Waktu Transaksi: `{transaction_time_str}`\n"
                f"Pesan API: `{escape_markdown(api_message, version=2)}`"
            )
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

            return {"success": False, "package_name": package_name_display, "error_message": "PROSES BERHASIL", "refunded_amount": deducted_balance, "status_message": "Pending (Retry)", "specific_action": "countdown_retry"}

        else:
            response.raise_for_status()
            
            if not api_status: 
                raise ValueError(api_message or f'API LOGIN mengembalikan status false untuk {package_code} (tidak dikenal sebagai sukses).')
            
            logging.info(f"Pembelian 30H (KMSP) untuk {phone} ({package_name_display}) berhasil diproses dengan respons status TRUE.")
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": f"Pembelian Paket (LOGIN - 30H)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": -deducted_balance, "timestamp": transaction_time_str, "status": "Berhasil",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()

            user_info = user_data["registered_users"][str(user_id)]
            admin_message = (
                f"✅ *PEMBELIAN 30H BERHASIL (LOGIN)!* ✅\n"
                f"User ID: `{user_id}`\n"
                f" (`{escape_markdown(user_info.get('first_name', 'N/A'), version=2)}` / `@{escape_markdown(user_info.get('username', 'N/A'), version=2)}`)\n"
                f"Nomor HP: `{phone}`\n"
                f"Kode Paket: `{package_code}`\n"
                f" ({escape_markdown(package_name_display, version=2)})\n"
                f"Metode Pembayaran: `{payment_method}`\n"
                f"Saldo Dipotong: `Rp{deducted_balance:,}`\n"
                f"Sisa Saldo: `Rp{user_info.get('balance', 0):,}`\n"
                f"Waktu Transaksi: `{transaction_time_str}`"
            )
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")

            return {"success": True, "package_name": package_name_display, "error_message": None, "refunded_amount": 0, "status_message": "Berhasil"}

    except Exception as e:
        error_type = type(e).__name__
        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)
        
                                                         
        TOKEN_EXPIRED_MESSAGE = "Terjadi kesalahan saat menampilkan data subscriber info!"
        is_token_error = False
        
        if isinstance(e, ValueError) and TOKEN_EXPIRED_MESSAGE in str(e):
            is_token_error = True
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "")
                if TOKEN_EXPIRED_MESSAGE in error_msg_from_api:
                    is_token_error = True
                    admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                pass
                                   

        if is_token_error:
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUWARSA* ⚠️\n"
                "Kemungkinan saat maintenance XL merefresh token login. Coba login ulang."
            )
        elif isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Waktu tunggu habis. Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
            admin_facing_error = "Request timed out after 60 seconds (KMSP API - 30H)"
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Gagal terhubung. Tidak dapat terhubung ke server (Connection Timeout)."
            admin_facing_error = "Connection timed out (KMSP API - 30H)"
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                if e.response and e.response.content:
                    response_json_content = {}
                    try:
                        response_json_content = e.response.json()
                    except json.JSONDecodeError:
                        pass

                    user_facing_error = f"Pesan dari server: {response_json_content.get('message', 'Terjadi kesalahan HTTP.')}"
                    admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - 30H): {response_json_content.get('message', 'No message')}. Raw: {e.response.text}"
                else:
                    user_facing_error = "Menerima respons HTTP yang tidak valid dari server."
                    admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - 30H) with no/invalid response content."
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respons yang tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} (KMSP API - 30H) with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)
        
        logging.error(f"Pembelian 30H (KMSP) gagal untuk user {user_id}, paket {package_code}. Error: {str(e)}")
        logging.error(traceback.format_exc())

        MAX_RETRIES = 10
        RETRY_DELAY = 11

        is_general_token_error = "access token is invalid" in admin_facing_error.lower() or \
                                 "token invalid" in admin_facing_error.lower() or \
                                 "token expired" in admin_facing_error.lower() or \
                                 "gagal login" in admin_facing_error.lower()

        if attempt < MAX_RETRIES and not is_token_error and not is_general_token_error:
            logging.info(f"Mencoba lagi pembelian 30H (KMSP) untuk {package_name_display} (percobaan {attempt + 1})... Menunda {RETRY_DELAY} detik.")
            await asyncio.sleep(RETRY_DELAY)
            return await execute_single_purchase_30h(update, context, user_id, package_code, package_name_display, phone, access_token, payment_method, deducted_balance, return_menu_callback_data, attempt + 1)
        else:
                                                                                   
            user_data["registered_users"][str(user_id)]["balance"] += deducted_balance
            user_data["registered_users"][str(user_id)]["transactions"].append({
                "type": "Pembelian Gagal (LOGIN - 30H) (Refund)", "package_code": package_code, "package_name": package_name_display, "phone": phone,
                "amount": deducted_balance, "timestamp": transaction_time_str, "status": "Gagal (Refund)",
                "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
            })
            simpan_data_ke_db()
            logging.info(f"Saldo user {user_id} dikembalikan {deducted_balance} karena kegagalan pembelian 30H (maksimal percobaan atau error token).")
        
            admin_message = (f"❌ *PEMBELIAN 30H GAGAL (LOGIN)!* ❌\n"
                             f"User ID: `{user_id}`\nNomor HP: `{phone}`\nKode Paket: `{package_code}`\n"
                             f"({escape_markdown(package_name_display, version=2)})\n"
                             f"Error: `{error_type}` - `{admin_facing_error}` (Saldo direfund)\n"
                             f"Total Percobaan: `{attempt}`")
            retry_data_key = uuid.uuid4().hex[:10]
            context.bot_data[f"retry_data_{retry_data_key}"] = json.dumps({
                'provider': 'kmsp', 
                'package_id_or_code': package_code,
                'package_name': package_name_display,
                'phone': phone,
                'payment_method': payment_method,
                'deducted_balance': deducted_balance,
                'return_menu_callback_data': return_menu_callback_data,
                'package_name_for_display': package_name_display 
            }).encode('utf-8').decode('utf-8')
            admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 COBA BELI LAGI (Admin)", callback_data=f"retry_single_{retry_data_key}")]])
            await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown", reply_markup=admin_keyboard)

            return {"success": False, "package_name": package_name_display, "error_message": "Token kadaluarsa", "refunded_amount": deducted_balance, "status_message": "Gagal (Token Kadaluarsa)", "fatal_error": True}

async def execute_custom_package_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, package_code: str, package_name: str, package_price: int, phone: str, access_token: str, payment_method: str, provider="kmsp"):
    url = ""
    api_price_or_fee = 0

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ewallet_fee FROM custom_packages WHERE code = ?", (package_code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        api_price_or_fee = result[0]
    
    if provider == "kmsp":
        url = f"https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&package_code={package_code}&phone={phone}&access_token={access_token}&payment_method={payment_method}&price_or_fee={api_price_or_fee}"
    else:
        logging.error(f"execute_custom_package_purchase dipanggil dengan provider tidak dikenal: {provider}")
        await context.bot.send_message(user_id, "Terjadi kesalahan internal. Provider API tidak dikenali.", parse_mode="Markdown")
        user_data["registered_users"][str(user_id)]["balance"] += package_price
        simpan_data_ke_db()
        return
    
    status_msg = await context.bot.send_message(user_id, f"Memproses pembelian paket kustom *{package_name}* dari LOGIN...\nHarap tunggu hingga 60 detik.", parse_mode="Markdown")
    loop = asyncio.get_running_loop()
    
    transaction_time = datetime.now()
    transaction_time_str = transaction_time.strftime('%Y-%m-%d %H:%M:%S')

    try:
        def blocking_api_call():
            return requests.get(url, timeout=58)

        api_response = await asyncio.wait_for(
            loop.run_in_executor(None, blocking_api_call),
            timeout=60.0
        )
        
        try:
            await status_msg.delete()
        except Exception:
            pass

        api_response.raise_for_status()
        api_result = api_response.json()
        
        if isinstance(api_result, list): 
            api_result = api_result[0] if api_result else {}

        if not api_result.get('status', False):
             raise ValueError(api_result.get("message", "Pembelian gagal menurut API LOGIN"))

        data = api_result.get("data", {})
        is_qris = data.get("is_qris", False)

        if payment_method == "QRIS" and is_qris:
            qris_data = data.get("qris_data", {})
            qris_code_raw_string = qris_data.get("qr_code")
            remaining_time = qris_data.get("remaining_time")
            if not qris_code_raw_string or not remaining_time:
                raise ValueError("Data QRIS dari API tidak lengkap.")
            qris_image_url = f"https://quickchart.io/qr?text={qris_code_raw_string}&size=300"
            pesan_info_qris = (
                f"Silakan scan QRIS untuk membayar *{package_name}*.\n\n"
                f"Setelah berhasil membayar, tekan tombol *'✅ Sudah Bayar'* di bawah.\n\n"
                f"⚠️ QRIS ini akan kedaluwarsa dalam *{remaining_time} detik*."
            )
            keyboard = [[InlineKeyboardButton("✅ Sudah Bayar", callback_data="qris_paid_manual_confirm")]]
            qris_photo_msg = await context.bot.send_photo(chat_id=user_id, photo=qris_image_url)
            qris_text_msg = await context.bot.send_message(user_id, pesan_info_qris, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            
                                         
            context.user_data['active_qris_messages'] = {
                'photo': qris_photo_msg.message_id,
                'text': qris_text_msg.message_id
            }
                                      

            context.job_queue.run_once(
                qris_expiration_job,
                remaining_time,
                data={'user_id': user_id, 'qris_message_id': qris_text_msg.message_id, 'qris_photo_id': qris_photo_msg.message_id},
                name=f"qris_expiration_custom_{user_id}_{qris_text_msg.message_id}"
            )
        elif payment_method == "DANA" and data.get("have_deeplink", False):
            deeplink_url = data.get("deeplink_data", {}).get("deeplink_url")
            keyboard = [[InlineKeyboardButton("💰 BAYAR SEKARANG", url=deeplink_url)]]
            await context.bot.send_message(user_id, f"✅ Pembelian *{package_name}* berhasil diproses. Silakan lanjutkan pembayaran.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(user_id, f"✅ Pembelian *{package_name}* berhasil diproses!", parse_mode="Markdown")

        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": f"Pembelian Paket Kustom ({provider.upper()})", "package_code": package_code, "package_name": package_name, "phone": phone,
            "amount": -package_price, "timestamp": transaction_time_str, "status": "Berhasil",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()
        
        user_info = user_data["registered_users"][str(user_id)]
        remaining_balance = user_info.get("balance", 0)
        user_first_name = user_info.get("first_name", "N/A")
        user_username = user_info.get("username", "N/A")

        admin_message = (
            f"📦 *PAKET KUSTOM BERHASIL ({provider.upper()})!*\n"
            f"User ID: `{user_id}` (`{user_first_name}` / `@{user_username}`)\n"
            f"Nomor: `{phone}`\n"
            f"Paket: `{package_name}` (`{package_code}`)\n"
            f"Harga: `Rp{package_price:,}`\n"
            f"Sisa Saldo User: `Rp{remaining_balance:,}`\n"
            f"Waktu Transaksi: `{transaction_time_str}`"
        )
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
            
    except Exception as e:
        try:
            await status_msg.delete()
        except Exception:
            pass

        user_facing_error = "Terjadi kesalahan yang tidak terduga."
        admin_facing_error = str(e)

                                                         
        TOKEN_EXPIRED_MESSAGE = "Terjadi kesalahan saat menampilkan data subscriber info!"
        is_token_error = False
        
        if isinstance(e, ValueError) and TOKEN_EXPIRED_MESSAGE in str(e):
            is_token_error = True
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "")
                if TOKEN_EXPIRED_MESSAGE in error_msg_from_api:
                    is_token_error = True
                    admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                pass
        
        if is_token_error:
            user_facing_error = (
                "⚠️ *TOKEN LOGIN ANDA KADALUWARSA* ⚠️\n"
                "Kemungkinan saat maintenance XL merefresh token login. Coba login ulang."
            )
                                   
        
        elif isinstance(e, asyncio.TimeoutError) or isinstance(e, requests.exceptions.ReadTimeout):
            user_facing_error = "Server tidak merespon dalam 60 detik (Timeout). Silakan coba lagi."
        elif isinstance(e, requests.exceptions.ConnectTimeout):
            user_facing_error = "Tidak dapat terhubung ke server (Connection Timeout)."
        elif isinstance(e, requests.exceptions.HTTPError):
            try:
                error_msg_from_api = e.response.json().get("message", "Terjadi kesalahan HTTP.")
                user_facing_error = f"Pesan dari API: {error_msg_from_api}"
                admin_facing_error = f"HTTP Error: {error_msg_from_api}"
            except (json.JSONDecodeError, AttributeError):
                user_facing_error = "Menerima respon yang tidak valid dari server."
                admin_facing_error = f"HTTP Error {e.response.status_code} with non-JSON response."
        elif isinstance(e, ValueError):
            user_facing_error = str(e)
            admin_facing_error = str(e)

        logging.error(f"Custom package purchase failed for user {user_id}, package {package_code}. Provider: {provider}. Full error: {str(e)}")
        logging.error(traceback.format_exc())

        user_data["registered_users"][str(user_id)]["balance"] += package_price
        user_data["registered_users"][str(user_id)]["transactions"].append({
            "type": f"Pembelian Kustom Gagal ({provider.upper()}) (Refund)", "package_code": package_code, "package_name": package_name, "phone": phone,
            "amount": package_price, "timestamp": transaction_time_str, "status": "Gagal (Refund)",
            "balance_after_tx": user_data["registered_users"][str(user_id)]["balance"]
        })
        simpan_data_ke_db()

        error_text = f"❌ Gagal membeli paket kustom *{package_name}*: `{user_facing_error}`\n💰 Saldo Anda sebesar *Rp{package_price:,}* telah dikembalikan."
        
        await context.bot.send_message(user_id, error_text, parse_mode="Markdown")

        user_info = user_data["registered_users"][str(user_id)]
        user_first_name = user_info.get("first_name", "N/A")

        admin_message = (f"❌ *PAKET KUSTOM GAGAL ({provider.upper()})!*\nUser ID: `{user_id}` (`{user_first_name}`)\nNomor: `{phone}`\nPaket: `{package_name}`\n"
                         f"Error: `{admin_facing_error}` (Saldo direfund)")
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
    
    await send_main_menu(update, context)

async def execute_unreg_package(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, current_phone: str, access_token: str, encrypted_package_code: str):
    url = f"https://golang-openapi-unregpackage-xltembakservice.kmsp-store.com/v1?api_key={KMSP_API_KEY}&access_token={access_token}&encrypted_package_code={encrypted_package_code}"
    logging.info(f"User {user_id} mencoba menghentikan paket (KMSP): {encrypted_package_code}")
    
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == 200:
            response_message = result.get("message", "Paket berhasil dihentikan.")
            await context.bot.send_message(user_id, f"✅ *STOP PAKET LOGIN BERHASIL!*:\n`{response_message}`", parse_mode="Markdown")
        else:
            error_message = result.get("message", "Gagal menghentikan paket.")
            await context.bot.send_message(user_id, f"❌ *STOP PAKET LOGIN GAGAL!*:\n`{error_message}`", parse_mode="Markdown")

    except Exception as e:
        error_detail = str(e)
        if isinstance(e, requests.exceptions.HTTPError):
            try:
                error_detail = e.response.json().get("message", "unknown error")
            except (json.JSONDecodeError, AttributeError):
                error_detail = f"HTTP Error {e.response.status_code} with non-JSON response."
        logging.error(f"Error saat unreg paket KMSP untuk user {user_id}: {e}")
        logging.error(traceback.format_exc())                     
        await context.bot.send_message(user_id, f"Terjadi kesalahan saat menghentikan paket LOGIN: {error_detail}.")

    await send_main_menu(update, context)

async def admin_confirm_user_top_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    parts = query.data.split('_')
    user_to_affect_id = int(parts[4])
    amount_to_add = int(parts[5])

    user_details = user_data.get("registered_users", {}).get(str(user_to_affect_id))
    if not user_details:
        await query.answer("User tidak ditemukan.", show_alert=True)
        return

                                       
    pending_info = user_details.pop("pending_top_up", {})
    user_msg_ids = pending_info.get("user_message_ids", [])

                                 
    user_details["balance"] += amount_to_add
    
                                                          
    new_balance = user_details["balance"]

    user_details["transactions"].append({
        "type": "Top Up", "amount": amount_to_add, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "status": "Berhasil", "admin_id": admin_id
    })
    simpan_data_ke_db()
    
                                       
    for msg_id in user_msg_ids:
        try:
            await context.bot.delete_message(chat_id=user_to_affect_id, message_id=msg_id)
        except Exception:
            pass

                                                          
    await context.bot.send_message(
        user_to_affect_id, 
        f"💰 Top Up Anda sebesar Rp{amount_to_add:,} telah berhasil ditambahkan oleh admin. Saldo Anda sekarang: Rp{new_balance:,}.",
        parse_mode="Markdown"
    )
    
                                                           
    await query.edit_message_text(
        f"✅ Berhasil konfirmasi top up Rp{amount_to_add:,} untuk user `{user_to_affect_id}`.\nSaldo baru user: Rp{new_balance:,}.",
        parse_mode="Markdown"
    )

async def admin_reject_user_top_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    parts = query.data.split('_')
    user_to_affect_id = int(parts[4])

    user_details = user_data.get("registered_users", {}).get(str(user_to_affect_id))
    if not user_details:
        await query.answer("User tidak ditemukan.", show_alert=True)
        return

    pending_info = user_details.pop("pending_top_up", {})
    user_msg_ids = pending_info.get("user_message_ids", [])
    simpan_data_ke_db()
    
    for msg_id in user_msg_ids:
        try:
            await context.bot.delete_message(chat_id=user_to_affect_id, message_id=msg_id)
        except Exception: pass
            
    await context.bot.send_message(user_to_affect_id, "❌ Maaf, permintaan top up Anda ditolak. Silakan hubungi admin untuk info lebih lanjut.")
    await query.edit_message_text(f"❌ Permintaan top up dari user `{user_to_affect_id}` telah ditolak.")
async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    await query.answer()

    all_users = list(user_data.get("registered_users", {}).items())
    
    if not all_users:
        await query.edit_message_text("Belum ada pengguna terdaftar.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")]]))
        return

    # Atur Paginasi
    USERS_PER_PAGE = 10 # Anda bisa ubah angka ini
    total_pages = math.ceil(len(all_users) / USERS_PER_PAGE)
    start_index = page * USERS_PER_PAGE
    end_index = start_index + USERS_PER_PAGE
    paginated_users = all_users[start_index:end_index]

    # Format Pesan
    text = f"👥 *Daftar Pengguna Terdaftar (Halaman {page + 1}/{total_pages})*\n\n"
    for i, (user_id, details) in enumerate(paginated_users, start=start_index + 1):
        first_name = details.get('first_name', 'N/A')
        username = details.get('username', 'N/A')
        balance = details.get('balance', 0)
        text += (
            f"*{i}.* `{user_id}`\n"
            f"   - Nama: {escape_markdown(first_name)}\n"
            f"   - Username: @{username}\n"
            f"   - Saldo: `Rp{balance:,}`\n\n"
        )

    # Buat Tombol Navigasi
    keyboard = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⏪ Sebelumnya", callback_data=f"admin_list_users_page_{page - 1}"))
    if end_index < len(all_users):
        nav_buttons.append(InlineKeyboardButton("Berikutnya ⏩", callback_data=f"admin_list_users_page_{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Admin", callback_data="admin_back_to_menu")])
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def akun_saya_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return

    user_id = update.effective_user.id
    logging.info(f"User {user_id} mengakses NOMOR SAYA (alur baru).")

    query = update.callback_query
    
    text = "Silakan masukan nomor yang ingin di cek status login nya..."
    keyboard = [[InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
                                               
        await delete_last_message(user_id, context)
        await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        
                                      
    context.user_data['next'] = 'handle_akun_saya_nomor_input'
    
async def hapus_akun_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    akun_list = user_data.get("registered_users", {}).get(str(user_id), {}).get("accounts", {})

    if not akun_list:
        await query.answer("Anda tidak memiliki akun untuk dihapus.", show_alert=True)
        return

    text = "*Pilih nomor yang ingin Anda hapus:*\n"
    buttons = []
    for nomor in akun_list.keys():
        buttons.append([InlineKeyboardButton(f"🗑️ Hapus {nomor}", callback_data=f"pilih_hapus_{nomor}")])
    
    buttons.append([InlineKeyboardButton("🔙 Kembali ke NOMOR SAYA", callback_data="akun_saya")])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def konfirmasi_hapus_akun(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_to_delete: str):
    query = update.callback_query
    text = (f"Anda yakin ingin menghapus akun *{phone_to_delete}*?\n"
            "Tindakan ini tidak dapat dibatalkan.")
    
    keyboard = [
        [InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"konfirmasi_hapus_{phone_to_delete}")],
        [InlineKeyboardButton("❌ Tidak, Batalkan", callback_data="batal_hapus_akun")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def eksekusi_hapus_akun(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_to_delete: str):
    if not await check_access(update, context):
        return
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await delete_last_message(user_id, context)

    if str(user_id) not in user_data["registered_users"] or phone_to_delete not in user_data["registered_users"][str(user_id)].get("accounts", {}):
        msg = await context.bot.send_message(user_id, f"❌ Akun `{phone_to_delete}` tidak ditemukan atau sudah terhapus.")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        await akun_saya_command_handler(update, context)
        return

    del user_data["registered_users"][str(user_id)]["accounts"][phone_to_delete]
    
    if user_data["registered_users"][str(user_id)].get("current_phone") == phone_to_delete:
        if user_data["registered_users"][str(user_id)]["accounts"]:
            user_data["registered_users"][str(user_id)]["current_phone"] = next(iter(user_data["registered_users"][str(user_id)]["accounts"]))
        else:
            user_data["registered_users"][str(user_id)]["current_phone"] = None

    user_details = user_data["registered_users"][str(user_id)]
                                                    
    if not user_details["accounts"] and not user_details["transactions"] and user_details["balance"] == 0:
        del user_data["registered_users"][str(user_id)]
        simpan_data_ke_db()
        logging.info(f"User {user_id} dan semua datanya dihapus karena tidak ada akun, transaksi, dan saldo 0.")
        msg = await context.bot.send_message(user_id, f"✅ Akun `{phone_to_delete}` dan semua data Anda telah dihapus karena tidak ada data tersisa.")
        bot_messages.setdefault(user_id, []).append(msg.message_id)
        return
    
    simpan_data_ke_db()
    logging.info(f"User {user_id} menghapus akun {phone_to_delete}")
    msg = await context.bot.send_message(user_id, f"✅ Akun `{phone_to_delete}` telah berhasil dihapus.")
    bot_messages.setdefault(user_id, []).append(msg.message_id)
    
    await akun_saya_command_handler(update, context)

async def show_custom_packages_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    custom_packages = user_data.get("custom_packages", {})

    query = update.callback_query

    if not custom_packages:
        text = "Belum ada paket lainnya yang tersedia saat ini."
        buttons = [[InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        if query:
            try:
                await query.edit_message_text(text, reply_markup=reply_markup)
            except Exception as e:
                if 'message is not modified' not in str(e):
                    logging.warning(f"Failed to edit message in show_custom_packages_for_user for empty packages: {e}. Sending new message.")
                    await context.bot.send_message(user_id, text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(user_id, text, reply_markup=reply_markup)
        return

                                       
    
                                          
    price_list_parts = ["*Daftar Harga Paket Lainnya:*\n"]
    for code, details in custom_packages.items():
        name = details.get('name', 'N/A')
        price = details.get('price', 0)
        price_list_parts.append(f"• *{name}*: `Rp{price:,}`")
    
                                                  
    text = "\n".join(price_list_parts)
    text += "\n\nSilakan pilih paket yang Anda inginkan di bawah ini."

                             

    buttons = []
    package_items = list(custom_packages.items())

    i = 0
    while i < len(package_items):
        row = []
        code1, details1 = package_items[i]
        name1 = details1.get('name', 'N/A')
        row.append(InlineKeyboardButton(f"{name1}", callback_data=f"view_custom_package_{code1}"))
        i += 1
        
        if i < len(package_items):
            code2, details2 = package_items[i]
            name2 = details2.get('name', 'N/A')
            row.append(InlineKeyboardButton(f"{name2}", callback_data=f"view_custom_package_{code2}"))
            i += 1
        
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🏠 Kembali ke Menu Utama", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if query:
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            if 'message is not modified' not in str(e):
                 logging.warning(f"Gagal mengedit pesan di show_custom_packages_for_user: {e}. Mengirim pesan baru.")
                 await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await context.bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=reply_markup)


def main():
                          
                                                        
                             
    BOT_TOKEN = os.getenv("BOT_TOKEN", "7852502840:AAE964uXKmAnuB7qBzfzBNcPwAwVDH5nXZc")
    
    if not BOT_TOKEN:
        logging.critical("BOT_TOKEN tidak ditemukan. Harap atur environment variable.")
        sys.exit(1)
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()
# --- PERBAIKAN: Menambahkan error handler ---
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
    app.add_error_handler(error_handler)
    # ----------------------------------------
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CommandHandler("akun_saya", akun_saya_command_handler))
    
    app.add_handler(CallbackQueryHandler(button))
    
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))


    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logging.info("Bot XL Tembak sedang berjalan...")
    try:
        app.run_polling()
    except Exception as e:
        logging.critical(f"Terjadi kesalahan fatal saat menjalankan bot: {e}", exc_info=True)
        shutdown_handler(None, None)
        sys.exit(1)

def shutdown_handler(sig, frame):
    logging.info("🔌 Menerima sinyal shutdown...")
    simpan_data_ke_db()
    logging.info("✅ Data berhasil disimpan. Bot dimatikan.")
    sys.exit(0)

if __name__ == '__main__':
    main()
