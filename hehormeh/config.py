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

_CATEGORY_INFO = json.load(open(ROOT_DIR / "categories" / f"{YEAR}.json"))
TRASH_CATEGORY = _CATEGORY_INFO["trash_category"]
ID2CAT = {int(cat_id): cat for cat_id, cat in _CATEGORY_INFO["categories"].items()}

ALLOWED_IMG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
HASH_SIZE = 8
