# database.py
import logging
import datetime
import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, List
import config

logger = logging.getLogger(__name__)

# Connection pool configuration
DB_POOL = pooling.MySQLConnectionPool(
    pool_name="bot_pool",
    pool_size=5,
    host=config.DB_HOST,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    database=config.DB_NAME,
    autocommit=True
)

def init_db():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_user_id BIGINT UNIQUE NOT NULL,
                name VARCHAR(255),
                username VARCHAR(255),
                balance DECIMAL(10,2) DEFAULT 0,
                date DATE,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX (telegram_user_id)
        """)
        
        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trx (
                id INT AUTO_INCREMENT PRIMARY KEY,
                wid VARCHAR(50),
                tid VARCHAR(50),
                user BIGINT,
                code VARCHAR(50),
                name VARCHAR(255),
                data TEXT,
                note TEXT,
                price DECIMAL(10,2),
                status VARCHAR(50),
                trxfrom VARCHAR(50),
                trxtype VARCHAR(50),
                date_cr TIMESTAMP,
                date_up TIMESTAMP,
                provider VARCHAR(50),
                INDEX (user),
                INDEX (status)
        """)
        
        # Create packages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paket_xl (
                package_code VARCHAR(50) PRIMARY KEY,
                package_name VARCHAR(255),
                package_harga DECIMAL(10,2),
                package_desc TEXT,
                package_status BOOLEAN DEFAULT TRUE,
                package_type VARCHAR(50),
                package_provider VARCHAR(50))
        """)
        
        conn.commit()
        logger.info("Database tables initialized successfully")
    except Error as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_db_connection():
    """Get a database connection from the pool"""
    try:
        return DB_POOL.get_connection()
    except Error as e:
        logger.error(f"Error getting database connection: {e}")
        return None

def add_user_if_not_exists(telegram_user_id: int, first_name: str, username: str = None) -> bool:
    """Add new user if not exists, returns True if user was added"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO users (telegram_user_id, name, username, date) "
            "VALUES (%s, %s, %s, %s)",
            (telegram_user_id, first_name, username, datetime.date.today())
        )
        affected_rows = cursor.rowcount
        conn.commit()
        
        if affected_rows > 0:
            logger.info(f"Added new user: {telegram_user_id} ({username})")
            return True
        return False
    except Error as e:
        logger.error(f"Error in add_user_if_not_exists: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_all_packages() -> List[Dict]:
    """Get all available packages"""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, IFNULL(h.harga, p.package_harga) AS harga_final 
            FROM paket_xl p 
            LEFT JOIN harga_paket h ON p.package_code = h.package_code 
            WHERE p.package_status = TRUE
            ORDER BY p.package_name ASC
        """)
        return cursor.fetchall()
    except Error as e:
        logger.error(f"Error getting packages: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_package_details(package_code: str) -> Optional[Dict]:
    """Get details for a specific package"""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, IFNULL(h.harga, p.package_harga) AS harga_final, h.harga as harga_kmsp 
            FROM paket_xl p 
            LEFT JOIN harga_paket h ON p.package_code = h.package_code 
            WHERE p.package_code = %s
        """, (package_code,))
        return cursor.fetchone()
    except Error as e:
        logger.error(f"Error getting package details: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_user_balance(telegram_user_id: int) -> Dict:
    """Get user balance and basic info"""
    conn = get_db_connection()
    if not conn:
        return {'balance': 0, 'username': None}
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT balance, username 
            FROM users 
            WHERE telegram_user_id = %s
        """, (telegram_user_id,))
        return cursor.fetchone() or {'balance': 0, 'username': None}
    except Error as e:
        logger.error(f"Error getting user balance: {e}")
        return {'balance': 0, 'username': None}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def log_transaction(trx_data: Dict) -> bool:
    """Log a transaction, returns True if successful"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trx (
                wid, tid, user, code, name, data, note, price, 
                status, trxfrom, trxtype, date_cr, date_up, provider
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            trx_data.get('wid'),
            trx_data.get('tid'),
            trx_data.get('user'),
            trx_data.get('code'),
            trx_data.get('name'),
            trx_data.get('data'),
            trx_data.get('note'),
            trx_data.get('price'),
            trx_data.get('status', 'pending'),
            trx_data.get('trxfrom', 'telegram_bot'),
            trx_data.get('trxtype', 'prepaid'),
            trx_data.get('timestamp', datetime.datetime.now()),
            trx_data.get('timestamp', datetime.datetime.now()),
            trx_data.get('provider', 'XL/AXIS')
        ))
        conn.commit()
        return True
    except Error as e:
        logger.error(f"Error logging transaction: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_user_balance(user_identifier: str, new_balance: float, by_username: bool = True) -> bool:
    """Update user balance, returns True if successful"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        if by_username:
            cursor.execute(
                "UPDATE users SET balance = %s WHERE username = %s",
                (new_balance, user_identifier)
            )
        else:
            cursor.execute(
                "UPDATE users SET balance = %s WHERE telegram_user_id = %s",
                (new_balance, user_identifier)
            )
        conn.commit()
        return cursor.rowcount > 0
    except Error as e:
        logger.error(f"Error updating balance: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_last_active(telegram_user_id: int) -> bool:
    """Update user's last active timestamp"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_user_id = %s",
            (telegram_user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Error as e:
        logger.error(f"Error updating last active: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
