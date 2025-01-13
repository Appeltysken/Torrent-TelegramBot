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
/hello - Получение ID
/get_torrents - Управление .torrent-файлами
/upload_torrent - Загрузить .torrent-файл
"""
    await update.message.reply_text(help_text)

def get_torrent_files(torrent_id, shift, limit=10):

    torrent_files = sorted(client.get_torrent(torrent_id).get_files(), key=lambda x: x.name)

    total_files = len(torrent_files)
    cur_page = shift // limit
    pages_total = (total_files + limit - 1) // limit

    start = shift
    end = min(shift + limit, total_files)
    torrent_files_shifted = torrent_files[start:end]

    return torrent_files_shifted, cur_page, pages_total

def filename_short(text, max_length=60):

    series_naming = re.compile(
        r'(S\d{1,2}[ ._\-]*E\d{1,2}|season[\s._\-]*\d{1,2}[\s._\-]*episode[\s._\-]*\d{1,2}|s\d{1,2}[ ._\-]*e\d{1,2}|[Ss]eason[\s._\-]*\d{1,2})'
    )

    match = series_naming.search(text)
    
    if match:
        series_part = match.group(0)
        extension = text.split('.')[-1]

        base_name = text[:text.rfind('.')]
        
        remaining_name = base_name.replace(series_part, '').strip('_-. ')
        return f"{series_part} {remaining_name}.{extension}" if extension else f"{series_part} {remaining_name}"
    
    else:
    
        if len(text) <= max_length:
            return text

        extension = text.split('.')[-1] if '.' in text else ''
        base_name = text[:text.rfind('.')] if extension else text

        cut_length = max_length - len(extension) - 5
        start_len = cut_length // 2
        end_len = cut_length - start_len

        return f"{base_name[:start_len]}...{base_name[-end_len:]}.{extension}" if extension else f"{base_name[:start_len]}...{base_name[-end_len:]}"
    
def construct_files_markup(torrent_id, page_num):

    torrent_files, cur_page, pages_total = get_torrent_files(torrent_id, shift=int(page_num) * LIMIT)

    keyboard = [
        [
            InlineKeyboardButton(
                ('✅' if el.selected else '❌') + filename_short(el.name),
                callback_data=f'torrent.{torrent_id}.page.{page_num}.file.{el.id}'
            )
        ] for el in torrent_files
    ]
    
    pagination_buttons = []
    if cur_page > 0:
        pagination_buttons.append(
            InlineKeyboardButton("⬅️ Предыдущая", callback_data=f'torrent.{torrent_id}.page.{cur_page - 1}')
        )
    if cur_page < pages_total - 1:
        pagination_buttons.append(
            InlineKeyboardButton("➡️ Следующая", callback_data=f'torrent.{torrent_id}.page.{cur_page + 1}')
        )

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
                    InlineKeyboardButton("▶️ Запустить", callback_data=f"torrent.{torrent_id}.start"),
                    InlineKeyboardButton("⏸️ Остановить", callback_data=f"torrent.{torrent_id}.pause"),
                    InlineKeyboardButton("⏏️ Удалить", callback_data=f"torrent.{torrent_id}.delete"),
                    InlineKeyboardButton("🔍 Управлять файлами", callback_data=f"torrent.{torrent_id}.page.0")
                ],
                [
                    InlineKeyboardButton("Показать статус", callback_data=f"torrent.{torrent_id}.status")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Торрент \"{client.get_torrent(int(torrent_id)).name}\".",
                reply_markup=reply_markup
            )
        
        case ['torrent', torrent_id, 'status']:
            torrent = client.get_torrent(int(torrent_id))
            status = f"""
            Название: {torrent.name}
            Состояние: {"Запущен" if torrent.status == "downloading" else "Остановлен"}
            Процент загрузки: {torrent.percent_done * 100:.2f}%
            Скорость загрузки: {torrent.rate_download / 1024:.2f} KB/s
            Скорость отдачи: {torrent.rate_upload / 1024:.2f} KB/s
            Активные пиры: {torrent.peers_connected}
            """
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data=f"torrent.{torrent_id}.menu"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(status, reply_markup=reply_markup)
        case ['torrent', torrent_id, 'start']:
            client.start_torrent(int(torrent_id))
            torrent = client.get_torrent(int(torrent_id))
            keyboard = [
                [
                    InlineKeyboardButton("▶️ Запустить", callback_data=f"torrent.{torrent_id}.start"),
                    InlineKeyboardButton("⏸️ Остановить", callback_data=f"torrent.{torrent_id}.pause"),
                    InlineKeyboardButton("⏏️ Удалить", callback_data=f"torrent.{torrent_id}.delete"),
                    InlineKeyboardButton("🔍 Управлять файлами", callback_data=f"torrent.{torrent_id}.page.0")
                ],
                [
                    InlineKeyboardButton("Показать статус", callback_data=f"torrent.{torrent_id}.status")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Торрент \"{torrent.name}\" запущен.",
                reply_markup=reply_markup
            )

        case ['torrent', torrent_id, 'pause']:
            client.stop_torrent(int(torrent_id))
            torrent = client.get_torrent(int(torrent_id))
            keyboard = [
                [
                    InlineKeyboardButton("▶️ Запустить", callback_data=f"torrent.{torrent_id}.start"),
                    InlineKeyboardButton("⏸️ Остановить", callback_data=f"torrent.{torrent_id}.pause"),
                    InlineKeyboardButton("⏏️ Удалить", callback_data=f"torrent.{torrent_id}.delete"),
                    InlineKeyboardButton("🔍 Управлять файлами", callback_data=f"torrent.{torrent_id}.page.0")
                ],
                [
                    InlineKeyboardButton("Показать статус", callback_data=f"torrent.{torrent_id}.status")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Торрент \"{torrent.name}\" остановлен.",
                reply_markup=reply_markup
            )

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