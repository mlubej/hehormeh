"""Useful constants and paths for the project."""

import json
import os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".."
DB_PATH = ROOT_DIR / "db"

VOTES_FILE = DB_PATH / "votes.csv"
IP_TO_USER_FILE = DB_PATH / "ip_to_user.csv"
USER_TO_IMAGE_FILE = DB_PATH / "user_to_image.csv"

YEAR = os.environ["YEAR"]
UPLOAD_PATH = Path("static") / YEAR

TRASH_ID, TRASH_CATEGORY = -1, "trash"
_CATEGORY_INFO = json.load(open(ROOT_DIR / "categories" / f"{YEAR}.json"))
ID2CAT = {int(cat_id): cat for cat_id, cat in _CATEGORY_INFO.items()}
ID2CAT_ALL = {**ID2CAT, TRASH_ID: TRASH_CATEGORY}
NUM_OF_CATS = len(ID2CAT)

ALLOWED_IMG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
HASH_SIZE = 8
