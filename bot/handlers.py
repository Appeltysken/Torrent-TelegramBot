import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, filters
from transmission.client import client
from config.config import USERS_WHITELIST

def restricted(func):
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in USERS_WHITELIST:
            print('restricted access attempt')
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@restricted
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Hello {update.effective_user.id}')