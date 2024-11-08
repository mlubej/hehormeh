"""Utility functions for the hehormeh app."""

import os
from enum import Enum
from pathlib import Path

import pandas as pd

from .config import (
    ALLOWED_IMG_EXTENSIONS,
    ID2CAT,
    ID2CAT_ALL,
    IP_TO_USER_FILE,
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


def is_host_admin(address: str):
    """Return whether the IP address belongs to the host."""
    return address == "127.0.0.1" or address == "0.0.0.0" or address == "localhost"


def has_valid_extension(filename: str) -> bool:
    """Check if the file has an allowed extension."""
    return Path(filename).suffix.lower() in ALLOWED_IMG_EXTENSIONS


def get_user_or_none(ip: str) -> str | None:
    """Get the user from the IP address."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_FILE, header=0).values)
    return mapping.get(ip, None)


def get_users_IPs() -> dict:
    """Get a dict with user as keys and the corresponding IP as the value."""
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    return {row.user: row.ip for row in pd.read_csv(IP_TO_USER_FILE, header=0).itertuples(index=False)}


def is_voting_valid(funny_votes, cringe_votes):
    """Check if the user has voted correctly.

    The user can only be the author of one image per category and should mark it for both categories.
    """
    score_values = set(funny_votes.values()) | set(cringe_votes.values())
    return all(v != -1 for v in score_values)


def category_voting_complete(category_id: int) -> bool:
    """TODO: finish this."""
    if not os.path.exists(VOTES_FILE):
        return False

    return True


# def meme_voting_finished(img_name: str) -> bool:
#     """Check if everyone has voted for a given category."""
#     upload_df = read_user_image_dataframe()
#     if upload_df is None:
#         return False

#     # if not os.path.exists(IP_TO_USER_FILE) or not os.path.exists(VOTES_FILE):
#     #     return False

#     # user_info_df = pd.read_csv(IP_TO_USER_FILE, header=0)
#     # user_info_df = user_info_df[~user_info_df.ip.apply(is_host_admin)]  # remove host from the list
#     # n_eligible_users = user_info_df.user.nunique()

#     # votes = pd.read_csv(VOTES_FILE, header=0)[["user", "cat_id"]].drop_duplicates()
#     # n_voting_users = votes[votes.cat_id == category_id].user.nunique()
#     # return n_voting_users == n_eligible_users


def get_next_votable_category_id() -> int:
    """Return the next category ID that the user can vote for."""
    categories = {cat_id: cat for cat_id, cat in ID2CAT.items() if not category_voting_complete(cat_id)}
    if len(categories) == 0:
        return list(ID2CAT.keys())[0]

    return list(categories.keys())[0]


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


def reset_image(image_path: str):
    """Reset image with given name."""
    image_path = Path(image_path)
    df = read_data(USER_TO_IMAGE_FILE)
    df = df[df.img_name != image_path.name]
    df.to_csv(USER_TO_IMAGE_FILE, index=False)
    image_path.unlink()
