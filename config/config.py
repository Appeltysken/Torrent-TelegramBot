import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TRANSMISSION_HOST = os.getenv('TRANSMISSION_HOST')
TRANSMISSION_PORT = int(os.getenv('TRANSMISSION_PORT'))
TRANSMISSION_USERNAME = os.getenv('TRANSMISSION_USERNAME')
TRANSMISSION_PASSWORD = os.getenv('TRANSMISSION_PASSWORD')
USERS_WHITELIST = [int(user_id) for user_id in os.getenv('USERS_WHITELIST', '').split(',') if user_id]