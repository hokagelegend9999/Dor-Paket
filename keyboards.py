# keyboards.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    """Menampilkan menu utama bot."""
    keyboard = [
        [InlineKeyboardButton("📱 Beli Paket Data XL", callback_data="purchase_xl_start")],
        [InlineKeyboardButton("❌ Tutup Menu", callback_data="close_menu")]
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
