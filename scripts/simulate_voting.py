"""Simulate upload of memes to the server."""

import os

import pandas as pd

os.environ["YEAR"] = "2024"
import random
import subprocess

import requests

from hehormeh.config import (
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)
from hehormeh.utils import get_next_votable_category_id

n_users = 5
users_and_ips = {f"user{i}": f"192.168.0.{i}" for i in range(1, n_users)}
# users_and_ips["matic"] = "192.168.1.X"
# users_and_ips["bobi"] = "192.168.1.X"

user_uploads_df = pd.read_csv(USER_TO_IMAGE_FILE, header=0)


# simulate voting
subprocess.run(f"rm -rf {VOTES_FILE}", shell=True)
while get_next_votable_category_id() is not None:
    cat_id = get_next_votable_category_id()

    for user, ip in users_and_ips.items():
        data = {"cat_id": cat_id}
        for idx, row in user_uploads_df[user_uploads_df.cat_id == cat_id].reset_index(drop=True).iterrows():
            if row.user == user:
                continue

            data = {
                **data,
                f"img_name_{idx}": row.img_name,
                f"funny_{idx}": random.randint(1, 5),
                f"cringe_{idx}": random.randint(1, 5),
            }

        headers = {"X-Test-IP": ip}
        r = requests.post("http://127.0.0.1:5001/vote", data=data, headers=headers)
