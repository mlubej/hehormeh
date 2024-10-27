"""Main module for the hehormeh Flask app."""

import hashlib
import os
from glob import glob
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .config import (
    ALLOWED_IMG_EXTENSIONS,
    CAT2ID,
    HASH_SIZE,
    ID2CAT,
    IP_TO_USER_FILE,
    ROOT_DIR,
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

app = Flask(__name__, static_folder=ROOT_DIR / "static")
app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024**2  # Limit upload data to 10 MiB


@app.route("/", methods=["GET", "POST"])
def index():
    """Display the main page of the app."""
    username = get_user_or_none(request.remote_addr)

    if request.method == "POST":
        cat = request.form["category"]
        funny_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "funny" in k}
        cringe_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "cringe" in k}

        # check user votes
        if not check_votes(funny_votes, cringe_votes):
            abort(
                400,
                description="You have not voted correctly! You can only be an author of one image per category, "
                "and you should mark it for both categories!",
            )

        kwargs = {"user": username, "cat_id": CAT2ID[cat]}
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


@app.route("/category_<int:cat_id>", methods=["GET"])
def category(cat_id: int):
    """Display the images for a given category."""
    images = [im for im in glob(f"{UPLOAD_PATH}/{ID2CAT[cat_id]}/*") if Path(im).suffix in ALLOWED_IMG_EXTENSIONS]
    return render_template("category.html", cat=ID2CAT[cat_id], category_id=cat_id, images=images)


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
            os.makedirs(ROOT_DIR / UPLOAD_PATH / cat, exist_ok=True)
            file.save(ROOT_DIR / UPLOAD_PATH / cat / hash_name)

            content = {"user": username, "cat_id": CAT2ID[cat], "img_name": hash_name}
            write_line(content, USER_TO_IMAGE_FILE)
            return redirect(request.url)

    uploaded_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT, images=uploaded_images)
