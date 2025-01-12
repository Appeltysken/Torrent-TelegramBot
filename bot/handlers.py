from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from functools import wraps
from config.config import USERS_WHITELIST
from transmission.client import client
import io
import re

LIMIT = 10

def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in USERS_WHITELIST:
            print(f"Access denied for user {user_id}")
            return

        return await func(update, context, *args, **kwargs)

    return wrapped

@restricted
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Hello {update.effective_user.id}')

