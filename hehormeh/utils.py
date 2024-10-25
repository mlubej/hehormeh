"""Utility functions for the hehormeh app."""

import os

import pandas as pd

from .config import (
    ALLOWED_IMG_EXTENSIONS,
    ID2CAT,
    IP_TO_USER_FILE,
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)


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


def get_user_or_none(ip: str) -> str | None:
    """Get the user from the IP address."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_FILE, names=["ip", "user"]).values)
    return mapping.get(ip, None)


# Function to check if the file has an allowed extension
def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG_EXTENSIONS


# Return a dict with images uploaded by a user for each category
def get_uploaded_images(username: str) -> dict | None:
    """Return a dict with images uploaded by a user for each category."""
    if not os.path.exists(USER_TO_IMAGE_FILE):
        return None

    df = pd.read_csv(USER_TO_IMAGE_FILE, names=["user", "cat", "image"])
    filtered_df = df[df["user"] == username]

    # Only take the last one in case a user uploaded more then one picture per category
    return filtered_df.groupby("cat")["image"].last().to_dict()
