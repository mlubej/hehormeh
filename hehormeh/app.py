"""Main module for the hehormeh Flask app."""

import hashlib
import os
from pathlib import Path

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
    Stages,
    generate_server_link_qr_code,
    get_image_and_author_info,
    get_next_votable_category_id,
    get_private_ip,
    get_uploaded_images,
    get_uploaded_images_info,
    get_user_or_none,
    get_users_ips,
    has_valid_extension,
    is_host_address,
    is_voting_valid,
    reset_image,
    score_memes,
    score_users,
    users_voting_status,
    users_voting_status_all,
    write_data,
)

app = Flask(__name__, static_folder=ROOT_DIR / "static")
app.config["UPLOAD_FOLDER"] = UPLOAD_PATH
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024**2  # Limit upload data to 10 MiB

CURRENT_STAGE = Stages.UPLOAD
CURRENT_CAT_ID = get_next_votable_category_id()


def get_remote_addr(request):
    """Use 'X-Test-Ip' header if present, otherwise fall back to `request.remote_addr`."""
    return request.headers.get("X-Test-IP", request.remote_addr)


@app.route("/", methods=["GET", "POST"])
def index():
    """Display the main page of the app."""
    global CURRENT_STAGE
    global CURRENT_CAT_ID

    username = get_user_or_none(get_remote_addr(request))
    if not username:
        return redirect(url_for("login"))

    new_cat_it = get_next_votable_category_id()
    if CURRENT_CAT_ID != new_cat_it:
        CURRENT_CAT_ID = new_cat_it
        CURRENT_STAGE = Stages.VIEWING

    user_voted_status = users_voting_status(new_cat_it)
    address = get_remote_addr(request)
    return render_template(
        "index.html",
        username=username,
        voted_status=user_voted_status.get(username, False),
        is_host_admin=is_host_address(address),
        curr_stage=CURRENT_STAGE.name,
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

        if new_username.lower() == "admin" and not is_host_address(get_remote_addr(request)):
            abort(403, description="You are not allowed to use this username!")

        content = [{"ip": get_remote_addr(request), "user": new_username}]
        write_data(content, IP_TO_USER_FILE)
        return redirect("/")

    return render_template("login.html", username=username)


@app.route("/vote", methods=["GET", "POST"])
def vote():
    """Display the images for a given category."""
    if CURRENT_STAGE != Stages.VOTING:
        abort(403, description="Voting not yet started!")

    username = get_user_or_none(get_remote_addr(request))
    if request.method == "POST":
        cat_id = int(request.form["cat_id"])
        img_names = {int(k.split("_")[-1]): v for k, v in request.form.items() if "img_name" in k}

        funny_votes = {int(k.split("_")[-1]): int(v) for k, v in request.form.items() if "funny" in k}
        cringe_votes = {int(k.split("_")[-1]): int(v) for k, v in request.form.items() if "cringe" in k}

        if not is_voting_valid(funny_votes, cringe_votes):
            abort(400, description="Make sure you vote for all the memes!")

        contents = []
        kwargs = {"user": username, "cat_id": cat_id}
        for idx, img_name in img_names.items():
            contents.append({**kwargs, "img_name": img_name, "funny": funny_votes[idx], "cringe": cringe_votes[idx]})

        write_data(contents, VOTES_FILE, check_cols=["user", "cat_id", "img_name"])
        return redirect("/")

    cat_id = get_next_votable_category_id()
    img_and_author_info = get_image_and_author_info(cat_id, username)
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

        content = [{"user": username, "cat_id": cat_id, "img_name": hash_name}]
        write_data(content, USER_TO_IMAGE_FILE)
        return redirect(request.url)


@app.route("/upload", methods=["POST", "GET"])
def upload():
    """Display the upload page of the app."""
    if request.method == "POST":
        return upload_handler(request)

    username = get_user_or_none(get_remote_addr(request))
    user_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT_ALL, trash_cat_id=TRASH_ID, user_images=user_images)


@app.route("/scoreboard", methods=["GET", "POST"])
def scoreboard():
    """Display the scoreboard."""
    global CURRENT_STAGE

    if CURRENT_STAGE not in [Stages.SCORE_CALC, Stages.WINNER_ANNOUNCEMENT]:
        abort(403, description="Scoreboard not ready yet!")

    if request.method == "POST":
        CURRENT_STAGE = Stages[request.form.get("stage")]
        return redirect("/scoreboard")

    return render_template("scoreboard.html", results={**score_memes(), **score_users()}, stage=CURRENT_STAGE.name)


@app.route("/admin", methods=["POST", "GET"])
def admin():
    """Display info about users and control staging."""
    global CURRENT_STAGE

    address = get_remote_addr(request)
    if not is_host_address(address):
        return redirect("/")

    if request.method == "POST":
        new_stage = request.form.get("stage")
        CURRENT_STAGE = Stages[new_stage] if new_stage else CURRENT_STAGE

        if request.form.get("generate_qr"):
            addr = get_private_ip()
            port = request.environ.get("SERVER_PORT")
            generate_server_link_qr_code(addr, port)
        return redirect(request.url)

    cat_id = get_next_votable_category_id()
    return render_template(
        "admin.html",
        categories=ID2CAT_ALL,
        user_uploads=get_uploaded_images_info(),
        user_votes=users_voting_status_all(),
        user_ips=get_users_ips(),
        trash_cat_id=TRASH_ID,
        current_cat=ID2CAT[cat_id] if cat_id is not None else None,
        curr_stage=CURRENT_STAGE.name,
        qr_code_img=f"static/{QR_CODE_IMAGE_FILE_NAME}",
    )


@app.route("/qr")
def qr():
    """Display QR code to connect to the server."""
    return render_template("qr.html", qr_code_img=f"static/{QR_CODE_IMAGE_FILE_NAME}")
