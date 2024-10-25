"""Useful constants and paths for the project."""

import os
from glob import glob
from pathlib import Path

ROOT_DIR = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DB_PATH = ROOT_DIR / "db"
STATIC_PATH = ROOT_DIR / "static"
UPLOAD_PATH = STATIC_PATH / "meme_files"

VOTES_FILE = DB_PATH / "votes.csv"
IP_TO_USER_FILE = DB_PATH / "ip_to_user.csv"
USER_TO_IMAGE_FILE = DB_PATH / "user_to_image.csv"

CATEGORIES = sorted(glob(f"{STATIC_PATH}/meme_files/*"))
ID2PATH = {idx: cat.split("static/")[-1] for idx, cat in enumerate(CATEGORIES)}
ID2CAT = {idx: cat.split("/")[-1] for idx, cat in ID2PATH.items()}
CAT2ID = {cat: idx for idx, cat in ID2CAT.items()}

ALLOWED_IMG_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
