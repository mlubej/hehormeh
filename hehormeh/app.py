"""Main module for the hehormeh Flask app."""

import hashlib
from pathlib import Path

import pandas as pd
from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .config import (
    CAT2ID,
    HASH_SIZE,
    ID2CAT,
    IP_TO_USER_FILE,
    STATIC_PATH,
    UPLOAD_PATH,
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)
from .utils import (
    check_votes,
    get_next_votable_category,
    get_uploaded_images,
    get_user_or_none,
    has_valid_extension,
    write_line,
)

app = Flask(__name__, static_folder=STATIC_PATH)
app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024**2  # Limit upload data to 10 MiB


@app.route("/", methods=["GET", "POST"])
def index():
    """Display the main page of the app."""
    username = get_user_or_none(request.remote_addr)

    if request.method == "POST":
        cat_id = request.form["cat_id"]
        funny_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "funny" in k}
        cringe_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "cringe" in k}

        # check user votes
        if not check_votes(funny_votes, cringe_votes):
            abort(
                400,
                description="You have not voted correctly! You can only be an author of one image per category, "
                "and you should mark it for both categories!",
            )

        kwargs = {"user": username, "cat_id": cat_id}
        for image_id in funny_votes.keys():
            contents = {**kwargs, "img_id": image_id, "funny": funny_votes[image_id], "cringe": cringe_votes[image_id]}
            write_line(contents, VOTES_FILE)

        return redirect("/")

    return render_template("index.html", username=username, categories=get_next_votable_category())


@app.route("/login", methods=["GET", "POST"])
def login():
    """Display the login page of the app."""
    # don't add duplicates to the csv file
    if request.method == "POST":
        username = request.form["user"]
        if not username:
            abort(400, description="Please enter a valid username!")

        content = {"ip": request.remote_addr, "user": username}
        write_line(content, IP_TO_USER_FILE)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/vote_<int:cat_id>", methods=["GET"])
def vote(cat_id: int):
    """Display the images for a given category."""
    df = pd.read_csv(USER_TO_IMAGE_FILE)
    df = df[df.cat_id == cat_id]
    df["img_path"] = df.img_name.apply(lambda name: f"static/meme_files/{ID2CAT[cat_id]}/{name}")
    img_and_author_info = {row.img_path: row.user == get_user_or_none(request.remote_addr) for _, row in df.iterrows()}
    return render_template("vote.html", cat_id=cat_id, cat=ID2CAT[cat_id], image_and_author_info=img_and_author_info)


@app.route("/upload", methods=["POST", "GET"])
def upload():
    """Display the upload page of the app."""
    username = get_user_or_none(request.remote_addr)
    if request.method == "POST":
        file = request.files.get("file", None)
        if not file or file.filename == "":
            return redirect(request.url)

        # TODO: Remove older images of users in case he/she already uploaded an image for a give category
        if file and has_valid_extension(file.filename):
            filename = secure_filename(file.filename)
            hash_name = hashlib.sha256(filename.encode()).hexdigest()[:HASH_SIZE] + Path(filename).suffix
            cat = request.form.get("category")
            file.save(UPLOAD_PATH / cat / hash_name)

            content = {"user": username, "cat_id": CAT2ID[cat], "img_name": hash_name}
            write_line(content, USER_TO_IMAGE_FILE)
            return redirect(request.url)

    uploaded_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT, images=uploaded_images)
