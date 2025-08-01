# keyboards.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    """Menampilkan menu utama bot."""
    keyboard = [
        [InlineKeyboardButton("📱 Panel Nomor XL", callback_data="panel_xl_menu")],
        [InlineKeyboardButton("🛒 Beli Paket Data XL", callback_data="purchase_xl_start")],
        [InlineKeyboardButton("❌ Tutup Menu", callback_data="close_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def panel_xl_keyboard():
    """Menampilkan menu setelah berhasil login OTP."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Cek Pulsa", callback_data="panel_cek_pulsa"),
            InlineKeyboardButton("📍 Cek Lokasi", callback_data="panel_cek_lokasi")
        ],
        [
            InlineKeyboardButton("📦 Cek Paket Aktif", callback_data="panel_cek_paket")
        ],
        [
            InlineKeyboardButton("🚪 Keluar / Ganti Nomor", callback_data="panel_logout")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def purchase_confirmation_keyboard():
    """Menampilkan tombol konfirmasi Ya/Tidak untuk pembelian."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya, Lanjutkan", callback_data='confirm_purchase_yes'),
            InlineKeyboardButton("❌ Batal", callback_data='confirm_purchase_no')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
