from flask import Flask, render_template, request, redirect, url_for

from glob import glob
import pandas as pd
import os

IP_TO_USER_CSV = "data/ip_to_user.csv"
app = Flask(__name__, static_folder="/Users/mlubej/play/hehormeh/data")

category_dirs = glob("data/meme_files/*")
categories = [path.split("/")[-1] for path in category_dirs]

# collect images
# images = {}
# for cat in category_dirs:
#     cat = cat.split("/")[-1]
#     images[cat] = glob(f"data/meme_files/{cat}/*.jpg")

# print(images)


# def hello_world():
#     return "<p>Hello, World!</p>"


@app.route("/", methods=["GET"])
def index():
    username = get_user(request.remote_addr)
    return render_template("index.html", username=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    # TODO: show categories only after being logged in
    # Show only the next category, not all of them
    # don't add duplicates to the csv file
    if request.method == "POST":
        mode = "w" if not os.path.exists(IP_TO_USER_CSV) else "a"
        with open(IP_TO_USER_CSV, mode) as f:
            user = request.form["user"]
            f.write(f"{request.remote_addr},{user}\n")

        return redirect(url_for("index"))

    return render_template("login.html")  # TODO: show that you are logged in as user


def get_user(ip: str) -> str | None:
    if not os.path.exists(IP_TO_USER_CSV):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_CSV, names=["ip", "user"]).values)
    return mapping.get(ip, None)


# https://stackoverflow.com/questions/35107885/how-to-generate-dynamic-urls-in-flask
# TODO: make them dynamic
@app.route("/categories", methods=["GET"])
def categories():
    is_registered = get_user(request.remote_addr) is not None
    print(is_registered)
    return render_template("categories.html", is_registered=is_registered)
