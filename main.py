# main.py
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
import config
import handlers
import database

# Konfigurasi logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani semua error yang tidak tertangkap."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main() -> None:
    """Memulai dan menjalankan bot."""
    database.init_db()
    application = Application.builder().token(config.BOT_TOKEN).build()
    application.add_error_handler(error_handler)

    # --- Daftarkan semua handler ---
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("menu", handlers.menu))
    application.add_handler(CommandHandler("cancel", handlers.cancel))

    # Daftarkan ConversationHandlers
    application.add_handler(handlers.purchase_xl_conv_handler)
    application.add_handler(handlers.otp_login_conv_handler)
    
    # Daftarkan CallbackQueryHandlers untuk fitur panel
    application.add_handler(CallbackQueryHandler(handlers.check_pulsa_handler, pattern='^panel_cek_pulsa$'))
    application.add_handler(CallbackQueryHandler(handlers.check_lokasi_handler, pattern='^panel_cek_lokasi$'))
    application.add_handler(CallbackQueryHandler(handlers.check_paket_handler, pattern='^panel_cek_paket$'))
    application.add_handler(CallbackQueryHandler(handlers.logout_handler, pattern='^panel_logout$'))
    application.add_handler(CallbackQueryHandler(handlers.unreg_paket_handler, pattern='^unreg_'))
    
    # Daftarkan handler umum untuk tombol menu (harus di akhir)
    application.add_handler(CallbackQueryHandler(handlers.route_handler))

    logger.info("Bot PPOB dimulai...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
