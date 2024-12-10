from telegram.ext import ApplicationBuilder
from config.config import TELEGRAM_BOT_TOKEN
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from bot.handlers import hello#, get_torrents, button, torrent_upload

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler('hello', hello))
#app.add_handler(CommandHandler('get_torrents', get_torrents))
#app.add_handler(CallbackQueryHandler(button))
#app.add_handler(MessageHandler(filters.Document.FileExtension('torrent'), torrent_upload))

if __name__ == "__main__":
    app.run_polling()