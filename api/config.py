import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

SECRET_AUTH = os.environ.get("SECRET_AUTH")
AUTH_TOKEN_LIFE = os.environ.get("AUTH_TOKEN_LIFE")

RT_SECRET = os.environ.get("RT_SECRET")
REFRESH_TOKEN_LIFE = os.environ.get("REFRESH_TOKEN_LIFE")

ALGORITHM = os.environ.get("ALGORITHM")