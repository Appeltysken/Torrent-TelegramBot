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

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Доступные команды:
/help - Показать список доступных команд
/hello - Приветствие
/get_torrents - Показать доступные торренты
/upload_torrent - Загрузить .torrent файл
"""
    await update.message.reply_text(help_text)

def get_torrent_files(torrent_id, shift, limit=10):
    cur_page = shift // limit

    torrent_files = sorted(client.get_torrent(torrent_id).get_files(), key=lambda x: x.name)

    pages_total = len(torrent_files) // limit

    if len(torrent_files) % limit:
        pages_total += 1

    torrent_files_shifted = torrent_files[shift:shift+limit]

    return torrent_files_shifted, cur_page, pages_total

def filename_filter(text):
    series_naming = re.compile(r'S\d+.{0,3}E\d+')

    if series_naming.search(text):
        return series_naming.search(text).group(0) + '.' + text.split('.')[-1]

    return text

def construct_files_markup(torrent_id, page_num):
    torrent_files, cur_page, pages_total = get_torrent_files(torrent_id, shift=int(page_num)*LIMIT)

    keyboard = [
        [
            InlineKeyboardButton(
                ('✅' if el.selected else '❌') + filename_filter(el.name),
                callback_data=f'torrent.{torrent_id}.page.{page_num}.file.{el.id}'
            )
        ] for el in torrent_files
    ]
    
    pagination_buttons = [
        InlineKeyboardButton(str(page_num + 1), callback_data=f'torrent.{torrent_id}.page')
        for page_num in range(pages_total) if page_num != cur_page
    ]

    if pagination_buttons:
        keyboard.append(pagination_buttons)
        
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data=f'torrent.{torrent_id}.menu')
    ])

    return InlineKeyboardMarkup(keyboard)


@restricted
async def get_torrents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    torrents = client.get_torrents()

    keyboard = [
        [
            InlineKeyboardButton(el.name, callback_data=f'torrent.{el.id}.menu'),
        ]
        for el in torrents
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Торренты:', reply_markup=reply_markup)

@restricted
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split('.')

    match data:
        case ['torrent', torrent_id, 'menu']:

            keyboard = [
                [
                    InlineKeyboardButton("Запустить", callback_data=f"torrent.{torrent_id}.start"),
                    InlineKeyboardButton("Остановить", callback_data=f"torrent.{torrent_id}.pause"),
                    InlineKeyboardButton("Удалить", callback_data=f"torrent.{torrent_id}.delete"),
                    InlineKeyboardButton("Управлять файлами", callback_data=f"torrent.{torrent_id}.page.0")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Торрент \"{client.get_torrent(int(torrent_id)).name}\".", reply_markup=reply_markup)

        case ['torrent', torrent_id, 'start']:
            client.start_torrent(int(torrent_id))
            await query.edit_message_text(f"Торрент {torrent_id} запущен.")

        case ['torrent', torrent_id, 'pause']:
            client.stop_torrent(int(torrent_id))
            await query.edit_message_text(f"Торрент {torrent_id} остановлен.")

        case ['torrent', torrent_id, 'delete']:
            client.remove_torrent(int(torrent_id))
            await query.edit_message_text(f"Торрент {torrent_id} удалён.")
            
        case ['torrent', torrent_id, 'start']:
            client.start_torrent(int(torrent_id))
            await query.edit_message_text(f"Торрент {torrent_id} запущен.")

        case ['torrent', torrent_id, 'page', page_num]:
            reply_markup = construct_files_markup(int(torrent_id), page_num)
            await query.edit_message_text('Файлы:', reply_markup=reply_markup)

        case ['torrent', torrent_id, 'page', page_num, 'file', file_id]:
            torrent_files = client.get_torrent(int(torrent_id)).get_files()

            wanted_unwanted_files = {
                'wanted': [],
                'unwanted': []
            }

            for el in torrent_files:
                status = el.selected

                if el.id == int(file_id):
                    status = not el.selected

                if status:
                    wanted_unwanted_files['wanted'].append(el.id)
                else:
                    wanted_unwanted_files['unwanted'].append(el.id)

            client.change_torrent(
                int(torrent_id),
                files_wanted=wanted_unwanted_files['wanted'],
                files_unwanted=wanted_unwanted_files['unwanted']
            )

            reply_markup = construct_files_markup(int(torrent_id), page_num)
            await query.edit_message_text('Файлы:', reply_markup=reply_markup)
            
        case ['torrent', torrent_id, 'download_all']:
            client.start_torrent(int(torrent_id))
            await query.edit_message_text(f'Запущен торрент: {torrent_id}')

        case ['torrent', torrent_id, 'menu']:
            
            keyboard = [
                [
                    InlineKeyboardButton("Запустить торрент", callback_data=f"torrent.{torrent_id}.download_all"),
                    InlineKeyboardButton("Управлять файлами", callback_data=f"torrent.{torrent_id}.page.0")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Торрент \"{client.get_torrent(int(torrent_id)).name}\".",
                reply_markup=reply_markup
            )
            
@restricted
async def upload_torrent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, отправьте .torrent файл.")

@restricted
async def receive_torrent_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.document:
            await update.message.reply_text("Пожалуйста, отправьте .torrent файл.")
            return

        document = update.message.document

        if not document.file_name.endswith(".torrent"):
            await update.message.reply_text("Этот файл не является .torrent файлом. Пожалуйста, отправьте корректный файл.")
            return

        file = await document.get_file()
        downloaded_file = await file.download_as_bytearray()
        
        torrent_bin = io.BytesIO(downloaded_file)
        torrent_bin.seek(0)

        torrent = client.add_torrent(torrent_bin, paused=True)
        
        keyboard = [
            [
                InlineKeyboardButton("Запустить торрент", callback_data=f"torrent.{torrent.id}.download_all"),
                InlineKeyboardButton("Управлять файлами", callback_data=f"torrent.{torrent.id}.page.0")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Торрент \"{torrent.name}\" успешно загружен.",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Error uploading torrent: {e}")
        await update.message.reply_text("Что-то пошло не так при загрузке торрента.")