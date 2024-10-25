import os
from glob import glob

import pandas as pd
from flask import Flask, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

STATIC_PATH = __file__.replace("main.py", "static")
UPLOAD_PATH = f"{STATIC_PATH}/meme_files"
DB_PATH = "./db"

IP_TO_USER_FILE = os.path.join(DB_PATH, "ip_to_user.csv")
VOTES_FILE = os.path.join(DB_PATH, "votes.csv")
USER_TO_IMAGE_FILE = os.path.join(DB_PATH, "user_to_image.csv")

ID2CAT_PATH = {idx: cat.split("static/")[-1] for idx, cat in enumerate(sorted(glob(f"{STATIC_PATH}/meme_files/*")))}
ID2CAT = {idx: cat.split("/")[-1] for idx, cat in ID2CAT_PATH.items()}
CAT2ID = {cat: idx for idx, cat in ID2CAT.items()}

app = Flask(__name__, static_folder=STATIC_PATH)
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH
app.config['MAX_CONTENT_LENGTH'] = 100 * 1000 * 1000 # Limit upload data to 100 MB

ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def check_votes(funny_votes, cringe_votes):
    author_votes_funny = [k for k, v in funny_votes.items() if v == -1]
    author_votes_cringe = [k for k, v in cringe_votes.items() if v == -1]
    if len(author_votes_funny) != 1 or len(author_votes_cringe) != 1:
        return False

    if author_votes_funny[0] != author_votes_cringe[0]:
        return False

    return True


def has_everyone_voted(category_id: int) -> bool:
    all_users = pd.read_csv(IP_TO_USER_FILE, names=["ip", "user"]).user.nunique()

    vote_cols = ["user", "cat_id", "meme_id", "funny", "cringe"]
    all_votes = pd.read_csv(VOTES_FILE, names=vote_cols)[["user", "cat_id"]].drop_duplicates()

    n_users_category = all_votes[all_votes["cat_id"] == category_id].user.nunique()
    return all_users == n_users_category


def get_eligible_categories() -> dict:
    categories = {cat_id: cat for cat_id, cat in ID2CAT.items() if not has_everyone_voted(cat_id)}

    if len(categories) == 0:
        return {}

    next_cat_id = sorted(list(categories.keys()))[0]
    return {next_cat_id: categories[next_cat_id]}


@app.route("/", methods=["GET", "POST"])
def index():
    username = get_user(request.remote_addr)

    if request.method == "POST":
        cat = request.form["category"]
        funny_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "funny" in k}
        cringe_votes = {int(k.split("_")[1]): int(v) for k, v in request.form.items() if "cringe" in k}

        # check user votes
        if not check_votes(funny_votes, cringe_votes):
            raise ValueError(
                (
                    "You have not voted correctly! You can only be an author of one image per category, "
                    "and you should mark it for both categories!"
                )
            )

        # TODO: read/write with dataframes?
        mode = "w" if not os.path.exists(VOTES_FILE) else "a"
        with open(VOTES_FILE, mode) as f:
            for image_id, vote in funny_votes.items():
                f.write(f"{username},{CAT2ID[cat]},{image_id},{vote},{cringe_votes[image_id]}\n")

        return redirect("/")

    return render_template("index.html", username=username, categories=get_eligible_categories())


@app.route("/login", methods=["GET", "POST"])
def login():
    # TODO: show categories only after being logged in
    # Show only the next category, not all of them
    # don't add duplicates to the csv file
    # TODO:Handle empty user
    if request.method == "POST":
        mode = "w" if not os.path.exists(IP_TO_USER_FILE) else "a"
        with open(IP_TO_USER_FILE, mode) as f:
            f.write(f'{request.remote_addr},{request.form["user"]}\n')

        return redirect(url_for("index"))

    return render_template("login.html")  # TODO: show that you are logged in as user


def get_user(ip: str) -> str | None:
    if not os.path.exists(IP_TO_USER_FILE):
        return None

    mapping = dict(pd.read_csv(IP_TO_USER_FILE, names=["ip", "user"]).values)
    return mapping.get(ip, None)


@app.route("/category_<int:cat_id>", methods=["GET"])
def category(cat_id: int):
    images = [im for ext in ALLOWED_IMG_EXTENSIONS
           for im in glob(f"static/meme_files/{ID2CAT[cat_id]}/*.{ext}")]

    return render_template("category.html", cat=ID2CAT[cat_id], category_id=cat_id, images=images)

# Function to check if the file has an allowed extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG_EXTENSIONS


# Return a dict with images uploaded by a user for each category
def get_uploaded_images(username: str) -> dict | None:
    if not os.path.exists(USER_TO_IMAGE_FILE):
        return None

    df = pd.read_csv(USER_TO_IMAGE_FILE, names=["user", "cat", "image"])
    filtered_df = df[df["user"] == username]

    # Only take the last one in case a user uploaded more then one picture per category
    return filtered_df.groupby("cat")["image"].last().to_dict()


@app.route("/upload", methods=["POST", "GET"])
def upload():
    username = get_user(request.remote_addr)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            print("No request")
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
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
                f.write(f'{username},{cat},static/meme_files/{cat}/{filename}\n')

            return redirect(request.url)

    uploaded_images = get_uploaded_images(username)
    return render_template("upload.html", categories=ID2CAT, images=uploaded_images)
