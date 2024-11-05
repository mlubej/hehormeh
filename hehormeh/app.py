"""Main module for the hehormeh Flask app."""

import hashlib
import os
from pathlib import Path

import pandas as pd
from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .config import (
    HASH_SIZE,
    ID2CAT,
    ID2CAT_ALL,
    IP_TO_USER_FILE,
    QR_CODE_IMAGE_FILE_NAME,
    ROOT_DIR,
    TRASH_ID,
    UPLOAD_PATH,
    USER_TO_IMAGE_FILE,
    VOTES_FILE,
)
from .utils import (
    check_votes,
    generate_server_link_QR_code,
    get_next_votable_category,
    get_uploaded_images,
    get_uploaded_images_info,
    get_user_or_none,
    has_valid_extension,
    is_host_admin,
    reset_image,
    write_line,
)

app = Flask(__name__, static_folder=ROOT_DIR / "static")
app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024**2  # Limit upload data to 10 MiB


def get_remote_addr(request):
    """Use 'X-Test-Ip' header if present, otherwise fall back to `request.remote_addr`."""
    return request.headers.get("X-Test-IP", request.remote_addr)


@app.route("/", methods=["GET", "POST"])
def index():
    """Display the main page of the app."""
    username = get_user_or_none(get_remote_addr(request))
    if not username:
        return redirect(url_for("login"))

    if request.method == "POST":
        cat_id = request.form["cat_id"]
        funny_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "funny" in k}
        cringe_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "cringe" in k}

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

    address = get_remote_addr(request)
    return render_template(
        "index.html", username=username, categories=get_next_votable_category(), is_host_admin=is_host_admin(address)
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Display the login page of the app."""
    username = get_user_or_none(get_remote_addr(request))
    if username:
        return redirect("/")

    if request.method == "POST":
        new_username = request.form["user"]
        if not new_username:
            abort(400, description="Please enter a valid username!")

        content = {"ip": get_remote_addr(request), "user": new_username}
        write_line(content, IP_TO_USER_FILE)
        return redirect("/")

    return render_template("login.html", username=username)


@app.route("/vote_<int:cat_id>", methods=["GET"])
def vote(cat_id: int):
    """Display the images for a given category."""
    df = pd.read_csv(USER_TO_IMAGE_FILE)
    df = df[df.cat_id == cat_id]
    df["img_path"] = df.img_name.apply(lambda name: UPLOAD_PATH / ID2CAT[cat_id] / name)
    img_and_author_info = {row.img_path: row.user == get_user_or_none(request.remote_addr) for _, row in df.iterrows()}
    return render_template("vote.html", cat_id=cat_id, cat=ID2CAT[cat_id], image_and_author_info=img_and_author_info)


def upload_handler(request):
    """Handle the normal category page."""
    username = get_user_or_none(get_remote_addr(request))
    image_to_reset = request.form.get("image_to_reset")

    if image_to_reset:
        reset_image(image_to_reset)
        return redirect(request.url)

    file = request.files.get("file", None)
    if not file or file.filename == "":
        return redirect(request.url)

    if file and has_valid_extension(file.filename):
        filename = secure_filename(file.filename)
        hash_name = hashlib.sha256(filename.encode()).hexdigest()[:HASH_SIZE] + Path(filename).suffix
        cat_id = int(request.form.get("cat_id"))

        os.makedirs(ROOT_DIR / UPLOAD_PATH / ID2CAT_ALL[cat_id], exist_ok=True)
        file.save(UPLOAD_PATH / ID2CAT_ALL[cat_id] / hash_name)

        content = {"user": username, "cat_id": cat_id, "img_name": hash_name}
        write_line(content, USER_TO_IMAGE_FILE)
        return redirect(request.url)


@app.route("/upload", methods=["POST", "GET"])
def upload():
    """Display the upload page of the app."""
    if request.method == "POST":
        return upload_handler(request)

    username = get_user_or_none(get_remote_addr(request))
    user_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT_ALL, trash_cat_id=TRASH_ID, user_images=user_images)


@app.route("/admin", methods=["POST", "GET"])
def admin():
    """Display info about users and control staging."""
    if request.method == "POST":
        generate_server_link_QR_code(request)
        return redirect(request.url)
    # TODO: add IPs of users

    address = get_remote_addr(request)
    if not is_host_admin(address):
        return redirect("/")

    return render_template(
        "admin.html",
        categories=ID2CAT_ALL,
        user_uploads=get_uploaded_images_info(),
        trash_cat_id=TRASH_ID,
        qr_code_img=f"static/{QR_CODE_IMAGE_FILE_NAME}",
    )


@app.route("/qr")
def qr():
    """Display QR code to connect to the server."""
    return render_template("qr.html", qr_code_img=f"static/{QR_CODE_IMAGE_FILE_NAME}")
