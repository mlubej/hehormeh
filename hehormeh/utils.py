"""Utility functions for the hehormeh app."""

import os
import socket
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
import qrcode
import qrcode.image.svg

from .config import (
    ALLOWED_IMG_EXTENSIONS,
    ID2CAT,
    ID2CAT_ALL,
    IP_TO_USER_FILE,
    QR_CODE_IMAGE_SAVE_PATH,
    UPLOAD_PATH,
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)


class Stages(Enum):
    """Enum of stages during meme night."""

    UPLOAD = 0
    VIEWING = 1
    VOTING = 2
    SCORE_CALC = 3
    WINNER_ANNOUNCEMENT = 4


def is_host_address(address: str):
    """Return whether the IP address belongs to the host."""
    return address in ["127.0.0.1", "0.0.0.0", "localhost"]


def has_valid_extension(filename: str) -> bool:
    """Check if the file has an allowed extension."""
    return Path(filename).suffix.lower() in ALLOWED_IMG_EXTENSIONS


def get_user_or_none(ip: str) -> str | None:
    """Get the user from the IP address."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_FILE, header=0)[["ip", "user"]].values)
    return mapping.get(ip, None)


def get_users_ips() -> dict:
    """Get a dict with user as keys and the corresponding IP as the value."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    return {row.user: row.ip for row in pd.read_csv(IP_TO_USER_FILE, header=0).itertuples(index=False)}


def is_voting_valid(funny_votes, cringe_votes):
    """Check if the user has voted correctly."""
    score_values = set(funny_votes.values()) | set(cringe_votes.values())
    return all(v != -1 for v in score_values)


def users_voting_status(cat_id: int) -> dict[str, bool]:
    """Return a dict with users and their voting status for a category."""
    user_info_df = pd.read_csv(IP_TO_USER_FILE, header=0)
    eligible_users = user_info_df[user_info_df.user != "admin"].user.unique()

    if not os.path.exists(VOTES_FILE):
        return {user: False for user in eligible_users}

    votes_df = pd.read_csv(VOTES_FILE, header=0)
    users_voted = votes_df[votes_df.cat_id == cat_id].user.unique()
    return {user: user in users_voted for user in eligible_users}


def users_voting_status_all() -> dict[str, dict[str, bool]]:
    """Gather the voting statuses for all categories."""
    return {cat_id: users_voting_status(cat_id) for cat_id in ID2CAT.keys()}


def category_voting_complete(category_id: int) -> bool:
    """Check if the voting for a category is complete."""
    return all(users_voting_status(category_id).values())


def get_next_votable_category_id() -> int | None:
    """Return the next category ID that the user can vote for."""
    categories = {cat_id: cat for cat_id, cat in ID2CAT.items() if not category_voting_complete(cat_id)}
    if not categories:
        return None
    return next(iter(categories))


def get_image_and_author_info(cat_id: int, username) -> dict:
    """Return a dict of image paths and info whether the user is the author."""
    df = read_user_image_dataframe()
    df = df[df.cat_id == cat_id]
    df["img_path"] = df.img_name.apply(lambda name: UPLOAD_PATH / ID2CAT[cat_id] / name)
    return {str(row.img_path): row.user == username for _, row in df.iterrows()}


def read_user_image_dataframe(username: str | None = None) -> pd.DataFrame | None:
    """Read the user2image dataframe."""
    if not os.path.exists(USER_TO_IMAGE_FILE):
        return None

    df = read_data(USER_TO_IMAGE_FILE)
    if username is not None:
        df = df[df["user"] == username]

    if df.empty:
        return None

    return df


def get_uploaded_images(username: str) -> dict[str, list[str]]:
    """Return a dict with images uploaded by a user for each category."""
    df = read_user_image_dataframe(username)
    if df is None:
        return dict()

    df["img_path"] = df.apply(lambda r: f"{UPLOAD_PATH}/{ID2CAT_ALL[r.cat_id]}/{r.img_name}", axis=1)
    return df.groupby("cat_id")["img_path"].apply(list).to_dict()


def get_uploaded_images_info() -> dict:
    """Return info about which user uploaded memes for which category."""
    df = read_user_image_dataframe()
    if df is None:
        return dict()

    def category_counts(user_df) -> dict[str, int]:
        """Get category counts for a given user-filtered dataframe."""
        cat_counts = user_df.groupby("cat_id")["img_name"].count().to_dict()
        return {cat: cat_counts.get(cat, 0) for cat in ID2CAT_ALL.keys()}

    return df.groupby("user").apply(category_counts).to_dict()


def read_data(csv_file: str) -> pd.DataFrame:
    """Read data from a file. First line is the header. Index is not set."""
    return pd.read_csv(csv_file, header=0)


def write_data(content: list[dict], csv_file: str, check_cols: list[str] | None = None):
    """Write a line to a file. If the line already exists, the line will be overwritten."""
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)

    existing_data = read_data(csv_file) if os.path.exists(csv_file) else None
    content = pd.DataFrame(content)

    new_data = pd.concat([existing_data, content]) if existing_data is not None else content
    new_data = new_data.drop_duplicates(check_cols, keep="last")
    new_data.to_csv(csv_file, index=False)


def is_host_admin(address: str):
    """Return whether the IP address belongs to the host."""
    return address == "127.0.0.1" or address == "0.0.0.0" or address == "localhost"


def reset_image(image_path: str):
    """Reset image with given name."""
    image_path = Path(image_path)
    df = read_data(USER_TO_IMAGE_FILE)
    df = df[df.img_name != image_path.name]
    df.to_csv(USER_TO_IMAGE_FILE, index=False)
    image_path.unlink()


def get_private_ip() -> str:
    """Return servers IP address via a hack chatgpt provided."""
    # Creates a socket connection to a remote host (Google DNS server) to get the local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external DNS server; doesn't actually send data
        s.connect(("8.8.8.8", 80))
        # Gets the private IP of the current machine
        private_ip = s.getsockname()[0]
    finally:
        s.close()
    return private_ip


def generate_server_link_qr_code(addr: str, port: str) -> None:
    """Generate QR code from the server link."""
    url = f"http://{addr}:{port}"
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage)
    with open(QR_CODE_IMAGE_SAVE_PATH, "wb") as qr:
        img.save(qr)


def idxmedian(series: pd.Series) -> str:
    """Return the index of the median value of the series."""
    return series.index[np.argsort(series.values)[len(series) // 2]]


def score_memes():
    """Evaluate meme scores."""
    votes = read_data(VOTES_FILE)
    votes["both"] = votes.funny + votes.cringe

    aggregations = [
        ("jazjaz_ravnovesja", "both", idxmedian),
        ("jazjaz_notranje_bolečine", "cringe", "idxmax"),
        ("smesen_ful_majkemi", "both", "idxmax"),
        ("najnajjazjaz", "funny", "idxmax"),
    ]

    results = {name: votes.groupby(["cat_id", "img_name"]).sum()[col].agg(func) for name, col, func in aggregations}

    # convert to full path
    return {award: f"{UPLOAD_PATH}/{ID2CAT[cat_id]}/{img_name}" for award, (cat_id, img_name) in results.items()}


def score_users():
    """Evaluate user scores."""
    uploads = read_data(USER_TO_IMAGE_FILE).set_index(["cat_id", "img_name"]).rename(columns={"user": "author"})
    votes = read_data(VOTES_FILE).set_index(["cat_id", "img_name"]).rename(columns={"user": "voter"})
    votes["both"] = votes.funny + votes.cringe

    votes = pd.merge(votes, uploads, left_index=True, right_index=True).reset_index()

    aggregations = [
        ("princesa_mediana", "both", idxmedian),
        ("grof_smehoslav", "funny", "idxmax"),
        ("skremžni_knez", "cringe", "idxmax"),
        ("meme_lord", "both", "idxmax"),
    ]

    return {name: votes.groupby("author").sum()[col].agg(func) for name, col, func in aggregations}
