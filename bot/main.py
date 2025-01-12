from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config.config import TELEGRAM_BOT_TOKEN
from bot.handlers import hello, get_torrents, button, upload_torrent_command, receive_torrent_file

def main():

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("hello", hello))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    