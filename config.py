from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST=os.environ.get("DB_HOST")
DB_PORT=os.environ.get("DB_PORT")
DB_NAME=os.environ.get("DB_NAME")
DB_USER=os.environ.get("DB_USER")
DB_PASSWORD=os.environ.get("DB_PASSWORD")

DISCORD_BOT_TOKEN=os.environ.get("DISCORD_BOT_TOKEN")

TEMP_FOLDER = "./temp"
TRACES_FOLDER = TEMP_FOLDER + "/trace"

if not os.path.exists(TRACES_FOLDER): os.makedirs(TRACES_FOLDER)