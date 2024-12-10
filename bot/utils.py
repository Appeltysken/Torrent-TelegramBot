import logging

def filename_filter(text, max_length=30):
    if len(text) > max_length:
        return text[:max_length-3] + '...'
    return text

logging.basicConfig(filename='logs/bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_message(message):
    logging.info(message)