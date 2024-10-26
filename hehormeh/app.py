"""Main module for the hehormeh Flask app."""

import os
from glob import glob

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .config import (
    ALLOWED_IMG_EXTENSIONS,
    CAT2ID,
    ID2CAT,
    IP_TO_USER_FILE,
    STATIC_PATH,
    UPLOAD_PATH,
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)
from .utils import allowed_file, check_votes, get_next_votable_category, get_uploaded_images, get_user_or_none

app = Flask(__name__, static_folder=STATIC_PATH)
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

        # TODO: read/write with dataframes?
        mode = "w" if not os.path.exists(VOTES_FILE) else "a"
        with open(VOTES_FILE, mode) as f:
            for image_id, vote in funny_votes.items():
                f.write(f"{username},{CAT2ID[cat]},{image_id},{vote},{cringe_votes[image_id]}\n")

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

        mode = "w" if not os.path.exists(IP_TO_USER_FILE) else "a"
        with open(IP_TO_USER_FILE, mode) as f:
            f.write(f'{request.remote_addr},{request.form["user"]}\n')

        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/category_<int:cat_id>", methods=["GET"])
def category(cat_id: int):
    """Display the images for a given category."""
    images = [im for ext in ALLOWED_IMG_EXTENSIONS for im in glob(f"static/meme_files/{ID2CAT[cat_id]}/*.{ext}")]

    return render_template("category.html", cat=ID2CAT[cat_id], category_id=cat_id, images=images)


@app.route("/upload", methods=["POST", "GET"])
def upload():
    """Display the upload page of the app."""
    username = get_user_or_none(request.remote_addr)
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            print("No request")
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            print("Empty filename")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            cat = request.form.get("category")
            print(cat)
            file.save(os.path.join(f"{UPLOAD_PATH}/{cat}", filename))

            # TODO: Remove older images of users in case he/she already uploaded an image for a give category
            mode = "w" if not os.path.exists(USER_TO_IMAGE_FILE) else "a"
            with open(USER_TO_IMAGE_FILE, mode) as f:
                f.write(f"{username},{cat},static/meme_files/{cat}/{filename}\n")

            return redirect(request.url)

    uploaded_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT, images=uploaded_images)
