"""Utility functions for the hehormeh app."""

import os
from pathlib import Path

import pandas as pd
from flask import abort

from .config import ALLOWED_IMG_EXTENSIONS, ID2CAT, IP_TO_USER_FILE, USER_TO_IMAGE_FILE, VOTES_FILE


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return Path(filename).suffix.lower() in ALLOWED_IMG_EXTENSIONS


def get_user_or_none(ip: str) -> str | None:
    """Get the user from the IP address."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_FILE, names=["ip", "user"]).values)
    return mapping.get(ip, None)


def check_votes(funny_votes, cringe_votes):
    """Check if the user has voted correctly.

    The user can only be the author of one image per category and should mark it for both categories.
    """
    author_votes_funny = [k for k, v in funny_votes.items() if v == -1]
    author_votes_cringe = [k for k, v in cringe_votes.items() if v == -1]
    if len(author_votes_funny) != 1 or len(author_votes_cringe) != 1:
        return False

    if author_votes_funny[0] != author_votes_cringe[0]:
        return False

    return True


def has_everyone_voted(category_id: int) -> bool:
    """Check if everyone has voted for a given category."""
    if not os.path.exists(IP_TO_USER_FILE) or not os.path.exists(VOTES_FILE):
        return False

    all_users = pd.read_csv(IP_TO_USER_FILE, names=["ip", "user"]).user.nunique()

    vote_cols = ["user", "cat_id", "meme_id", "funny", "cringe"]
    all_votes = pd.read_csv(VOTES_FILE, names=vote_cols)[["user", "cat_id"]].drop_duplicates()

    n_users_category = all_votes[all_votes["cat_id"] == category_id].user.nunique()
    return all_users == n_users_category


def get_next_votable_category() -> dict:
    """Return the next category that the user can vote for."""
    categories = {cat_id: cat for cat_id, cat in ID2CAT.items() if not has_everyone_voted(cat_id)}

    if len(categories) == 0:
        return {}

    next_cat_id = sorted(list(categories.keys()))[0]
    return {next_cat_id: categories[next_cat_id]}


def get_uploaded_images(username: str) -> dict:
    """Return a dict with images uploaded by a user for each category."""
    if not os.path.exists(USER_TO_IMAGE_FILE):
        return dict()

    df = read_data(USER_TO_IMAGE_FILE)
    if df.empty:
        return dict()

    df = df[df["user"] == username]
    df["img_path"] = df.apply(lambda r: f"static/meme_files/{ID2CAT[r.cat_id]}/{r.img_name}", axis=1)

    # Only take the last one in case a user uploaded more then one picture per category
    # TODO: make sure there is only one image per category
    return df.groupby("cat_id")["img_path"].last().to_dict()


def read_data(csv_file: str) -> pd.DataFrame:
    """Read data from a file. First line is the header. Index is not set."""
    return pd.read_csv(csv_file, header=0)


def write_line(content: dict, csv_file: str):
    """Write a line to a file. If the line already exists, the line will be overwritten."""
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)

    columns = list(content.keys())
    existing_data = read_data(csv_file) if os.path.exists(csv_file) else pd.DataFrame(columns=columns)

    if not existing_data.empty and set(columns) != set(existing_data.columns):
        abort(400, description="Content does not match existing data.")

    new_data = pd.concat([existing_data, pd.DataFrame(content, index=[0])]).drop_duplicates(keep="last")
    new_data.to_csv(csv_file, index=False)


def delete_line(csv_file: str, column_name: str, match_value):
    """Delete line in csv_file in which column column_name contains value match_value."""
    df = read_data(csv_file) if os.path.exists(csv_file) else abort(400, description=f"{csv_file} does not exist")

    df = df[eval(f"df.{column_name}") != match_value]
    df.to_csv(csv_file, index=False)
