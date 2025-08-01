# database.py
import logging
import datetime
import mysql.connector
from mysql.connector import Error
import config

logger = logging.getLogger(__name__)

def init_db():
    logger.info("Database MySQL siap digunakan.")

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        return conn
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None

def add_user_if_not_exists(telegram_user_id: int, first_name: str, username: str = None):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT telegram_user_id FROM users WHERE telegram_user_id = %s", (telegram_user_id,))
        if not cursor.fetchone():
            insert_query = "INSERT INTO users (telegram_user_id, name, username, balance, date) VALUES (%s, %s, %s, %s, %s)"
            today_date = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute(insert_query, (telegram_user_id, first_name, username, 0, today_date))
            conn.commit()
            logger.info(f"User {telegram_user_id} ({username}) ditambahkan ke DB.")
    except Error as e:
        logger.error(f"Error di add_user_if_not_exists: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_all_packages():
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.*, IFNULL(h.harga, p.package_harga) AS harga_final FROM paket_xl p LEFT JOIN harga_paket h ON p.package_code = h.package_code ORDER BY p.package_name ASC")
    packages = cursor.fetchall()
    cursor.close()
    conn.close()
    return packages

def get_package_details(package_code):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.*, IFNULL(h.harga, p.package_harga) AS harga_final, h.harga as harga_kmsp FROM paket_xl p LEFT JOIN harga_paket h ON p.package_code = h.package_code WHERE p.package_code = %s", (package_code,))
    package = cursor.fetchone()
    cursor.close()
    conn.close()
    return package

def get_user_balance(telegram_user_id):
    conn = get_db_connection()
    if not conn: return {'balance': 0, 'username': None}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT balance, username FROM users WHERE telegram_user_id = %s", (telegram_user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user if user else {'balance': 0, 'username': None}

def log_transaction(trx_data):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    query = "INSERT INTO trx (wid, tid, user, code, name, data, note, price, status, trxfrom, trxtype, date_cr, date_up, provider) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    try:
        cursor.execute(query, (trx_data['wid'], trx_data['tid'], trx_data['user'], trx_data['code'], trx_data['name'], trx_data['data'], trx_data['note'], trx_data['price'], trx_data['status'], 'telegram_bot', 'prepaid', trx_data['timestamp'], trx_data['timestamp'], 'XL/AXIS'))
        conn.commit()
    except Error as e:
        logger.error(f"Error logging transaction: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_user_balance(username, new_balance):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET balance = %s WHERE username = %s", (new_balance, username))
        conn.commit()
    except Error as e:
        logger.error(f"Error updating balance: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
