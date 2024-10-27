"""Simulate upload of memes to the server."""

import os

os.environ["YEAR"] = "2024"

import subprocess
from glob import glob

import requests

from hehormeh.config import ID2CAT, IP_TO_USER_FILE, ROOT_DIR, UPLOAD_PATH, USER_TO_IMAGE_FILE

n_users = 6
users_and_ips = {f"user{i}": f"192.168.0.{i}" for i in range(1, n_users)}
users_and_ips["admin"] = "127.0.0.1"

# log in users
subprocess.run(f"rm -rf {IP_TO_USER_FILE}", shell=True)
for user, ip in users_and_ips.items():
    headers = {"X-Test-IP": ip}
    r = requests.post("http://127.0.0.1:5001/login", data={"user": user}, headers=headers)


# simulate uploads
subprocess.run(f"rm -rf {UPLOAD_PATH}", shell=True)
subprocess.run(f"rm -rf {USER_TO_IMAGE_FILE}", shell=True)
for idx, (user, ip) in enumerate(users_and_ips.items()):
    for cat_id, cat in ID2CAT.items():
        image_path = glob(str(ROOT_DIR / "meme_dump" / "2024_fake" / cat / "*"))[idx]

        headers = {"X-Test-IP": ip}
        r = requests.post(
            "http://127.0.0.1:5001/upload",
            files={"file": open(image_path, "rb")},
            data={"cat_id": cat_id},
            headers=headers,
        )
