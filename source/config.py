import os
from dotenv import load_dotenv
import pytz

load_dotenv()

# Bot & Database Configuration
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Application Constants
ATTACHMENT_DIR = "attachments"
TIMEZONE = pytz.timezone('CET')