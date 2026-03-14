import os
import shutil
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, abort
)
from werkzeug.utils import secure_filename

from models import (
    init_db,
    create_user,
    get_user_by_username, verify_password,

    list_shops, get_shop, create_shop, update_shop, delete_shop,

    list_info_summaries, get_info, create_info, update_info, delete_info,
    list_info_dates_for_shop,

    list_exp_items, create_exp_item, get_exp_item, update_exp_item, delete_exp_item,

    list_contacts, create_contact, get_contact, update_contact, delete_contact,

    list_brands, get_brand, create_brand, update_brand, delete_brand,

    list_fast_items, get_fast_item, create_fast_item, update_fast_item, delete_fast_item,
    list_fast_items_for_shop_and_date,
)

from pdf_utils import build_exp_items_pdf, build_fast_items_pdf

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
UPLOAD_ROOT = STATIC_DIR / "uploads"


# ---------------- Helpers ----------------
def slugify(name: str) -> str:
    s = name.strip().lower()
    s = "".join(ch if ch.isalnum() else "-" for ch in s)
    s = "-".join(filter(None, s.split("-")))
    return s or "shop"


def shop_folder(shop_name: str) -> Path:
    return UPLOAD_ROOT / slugify(shop_name)


def ensure_shop_folders(shop_name: str) -> None:
    root = shop_folder(shop_name)
    (root / "shop_photo").mkdir(parents=True, exist_ok=True)
    (root / "exp_item").mkdir(parents=True, exist_ok=True)
    (root / "other_messages").mkdir(parents=True, exist_ok=True)


def remove_shop_folder(shop_name: str) -> None:
    root = shop_folder(shop_name)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def move_shop_folder(old_name: str, new_name: str) -> None:
    old_root = shop_folder(old_name)
    new_root = shop_folder(new_name)

    if old_root.exists() and old_root != new_root:
        if new_root.exists():
            shutil.rmtree(new_root, ignore_errors=True)
        new_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_root), str(new_root))

    ensure_shop_folders(new_name)


def allowed_image(filename: str) -> bool:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return ext in {"png", "jpg", "jpeg", "webp"}


# ---------------- Other TXT helpers ----------------
def other_txt_path(shop_name: str, info_id: int) -> Path:
    ensure_shop_folders(shop_name)
    return shop_folder(shop_name) / "other_messages" / f"other_info_{info_id}.txt"


def write_other_message_txt(shop_name: str, info_id: int, inspector: str, message: str) -> str:
    now = datetime.now()
    content = (
        f"Shop : {shop_name}\n"
        f"Date : {now.strftime('%Y-%m-%d')}\n"
        f"Time : {now.strftime('%H:%M:%S')}\n"
        f"Inspector : {inspector}\n\n"
        f"Message :\n"
        f"{(message or '').strip()}\n"
    )

    pth = other_txt_path(shop_name, info_id)
    tmp = pth.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(pth)

    print("✅ OTHER TXT SAVED/UPDATED =>", pth)
    return str(pth.relative_to(APP_DIR)).replace("\\", "/")


def delete_other_message_txt(shop_name: str, info_id: int) -> None:
    pth = other_txt_path(shop_name, info_id)
    try:
        if pth.exists():
            pth.unlink()
            print("🗑️ OTHER TXT DELETED =>", pth)
    except Exception as e:
        print("⚠️ OTHER TXT DELETE FAILED:", e)


def created_date_only(value: str) -> str:
    return (value or "").split(" ")[0]


def created_time_only(value: str) -> str:
    parts = (value or "").split(" ")
    return parts[1] if len(parts) > 1 else ""


# ---------------- App ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

DB_PATH = str(APP_DIR / "app.db")

# ---------------- Startup ----------------
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

if not os.path.exists(DB_PATH):
    open(DB_PATH, "w").close()

init_db(DB_PATH)

DEFAULT_ADMIN_USER = "itk"
DEFAULT_ADMIN_PASS = "itk5892"

DEFAULT_USER_USER = "user"
DEFAULT_USER_PASS = "123"

try:
    if not get_user_by_username(DB_PATH, DEFAULT_ADMIN_USER):
        create_user(DB_PATH, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS, "admin")
        print("✅ Default admin created:", DEFAULT_ADMIN_USER)
except Exception as e:
    print("⚠️ Admin create skipped:", e)

try:
    if not get_user_by_username(DB_PATH, DEFAULT_USER_USER):
        create_user(DB_PATH, DEFAULT_USER_USER, DEFAULT_USER_PASS, "user")
        print("✅ Default user created:", DEFAULT_USER_USER)
except Exception as e:
    print("⚠️ User create skipped:", e)

admin_u = os.environ.get("FIRST_ADMIN_USER")
admin_p = os.environ.get("FIRST_ADMIN_PASS")
if admin_u and admin_p:
    try:
        if not get_user_by_username(DB_PATH, admin_u):
            create_user(DB_PATH, admin_u, admin_p, "admin")
    except Exception:
        pass

user_u = os.environ.get("FIRST_USER_USER")
user_p = os.environ.get("FIRST_USER_PASS")
if user_u and user_p:
    try:
        if not get_user_by_username(DB_PATH, user_u):
            create_user(DB_PATH, user_u, user_p, "user")
    except Exception:
        pass


# ---------------- Auth helpers ----------------
def current_user():
    return session.get("user")


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        u_ = current_user()
        if not u_:
            return redirect(url_for("login"))
        if u_.get("role") != "admin":
            flash("Admin only.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)

    return wrapper


# ---------------- Routes ----------------
@app.get("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = (request.form.get("role") or "").strip().lower()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if role not in {"admin", "user"}:
            flash("Select a valid role.", "danger")
            return render_template("login.html")

        user = get_user_by_username(DB_PATH, username)

        if not user or not verify_password(password, user["password_hash"]):
            flash("Invalid username or password", "danger")
            return render_template("login.html")

        if role != user["role"]:
            flash("Invalid role selected", "danger")
            return render_template("login.html")

        session["user"] = {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
        flash("Login successful", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------------- Shops ----------------
@app.get("/shops")
@login_required
def shops():
    items = list_shops(DB_PATH)
    return render_template("shops/list.html", shops=items)


@app.route("/shops/add", methods=["GET", "POST"])
@admin_required
def shops_add():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        location = (request.form.get("location") or "").strip()
        shop_type = (request.form.get("shop_type") or "").strip()
        pos_system = (request.form.get("pos_system") or "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not location:
            errors.append("Location is required.")
        if shop_type not in {"Co-Op", "Mini Co-Op", "Regional"}:
            errors.append("Shop type is required.")
        if pos_system not in {"Yes", "No"}:
            errors.append("POS System selection is required.")

        photo = request.files.get("shop_photo")
        photo_rel = None
        if photo and photo.filename:
            if not allowed_image(photo.filename):
                errors.append("Shop photo must be png/jpg/jpeg/webp.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("shops/add_edit.html", mode="add", shop=None)

        ensure_shop_folders(name)

        if photo and photo.filename:
            fn = secure_filename(photo.filename)
            dest = shop_folder(name) / "shop_photo" / f"shop_{int(datetime.utcnow().timestamp())}_{fn}"
            photo.save(dest)
            photo_rel = str(dest.relative_to(STATIC_DIR)).replace("\\", "/")

        create_shop(DB_PATH, name, location, shop_type, pos_system, photo_rel)
        flash("Shop saved", "success")
        return redirect(url_for("shops"))

    return render_template("shops/add_edit.html", mode="add", shop=None)


@app.route("/shops/<int:shop_id>/edit", methods=["GET", "POST"])
@admin_required
def shops_edit(shop_id):
    shop = get_shop(DB_PATH, shop_id)
    if not shop:
        abort(404)

    if request.method == "POST":
        new_name = (request.form.get("name") or "").strip()
        location = (request.form.get("location") or "").strip()
        shop_type = (request.form.get("shop_type") or "").strip()
        pos_system = (request.form.get("pos_system") or "").strip()

        errors = []
        if not new_name:
            errors.append("Name is required.")
        if not location:
            errors.append("Location is required.")
        if shop_type not in {"Co-Op", "Mini Co-Op", "Regional"}:
            errors.append("Shop type is required.")
        if pos_system not in {"Yes", "No"}:
            errors.append("POS System selection is required.")

        photo = request.files.get("shop_photo")
        photo_rel = shop["shop_photo"]
        if photo and photo.filename:
            if not allowed_image(photo.filename):
                errors.append("Shop photo must be png/jpg/jpeg/webp.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("shops/add_edit.html", mode="edit", shop=shop)

        if shop["name"] != new_name:
            move_shop_folder(shop["name"], new_name)

        if photo and photo.filename:
            ensure_shop_folders(new_name)
            fn = secure_filename(photo.filename)
            dest = shop_folder(new_name) / "shop_photo" / f"shop_{int(datetime.utcnow().timestamp())}_{fn}"
            photo.save(dest)
            photo_rel = str(dest.relative_to(STATIC_DIR)).replace("\\", "/")

        update_shop(DB_PATH, shop_id, new_name, location, shop_type, pos_system, photo_rel)
        flash("Shop updated", "success")
        return redirect(url_for("shops"))

    return render_template("shops/add_edit.html", mode="edit", shop=shop)


@app.post("/shops/<int:shop_id>/delete")
@admin_required
def shops_delete(shop_id):
    shop = get_shop(DB_PATH, shop_id)
    if not shop:
        abort(404)

    delete_shop(DB_PATH, shop_id)
    remove_shop_folder(shop["name"])

    flash("Shop deleted", "warning")
    return redirect(url_for("shops"))


# ---------------- Information ----------------
@app.get("/information")
@login_required
def information():
    summaries = list_info_summaries(DB_PATH)
    return render_template("information/list.html", summaries=summaries)


@app.route("/information/add", methods=["GET", "POST"])
@admin_required
def info_add():
    shops_list = list_shops(DB_PATH)

    if request.method == "POST":
        shop_id = request.form.get("shop_id")
        ratings = {
            "clean": request.form.get("clean"),
            "management": request.form.get("management"),
            "environment": request.form.get("environment"),
            "quality": request.form.get("quality"),
        }
        expired = request.form.get("expired")
        expired_amount = (request.form.get("expired_amount") or "").strip()
        other = request.form.get("other")
        other_message = (request.form.get("other_message") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        for k, v in ratings.items():
            if v not in {"Best", "Good", "Not Bad", "Super"}:
                errors.append(f"{k.title()} rating is required.")
        if expired not in {"Yes", "No"}:
            errors.append("Expired Items Yes/No is required.")
        if expired_amount == "":
            errors.append("Expired Items Amount is required (0 allowed).")
        else:
            try:
                int(expired_amount)
            except:
                errors.append("Expired Items Amount must be a number.")
        if other not in {"Yes", "No"}:
            errors.append("Other Yes/No is required.")
        if other == "Yes" and not other_message:
            errors.append("Other message is required when Other = Yes.")

        photo = request.files.get("expired_photo")
        photo_rel = None
        if photo and photo.filename:
            if not allowed_image(photo.filename):
                errors.append("Expired photo must be png/jpg/jpeg/webp.")
        if expired == "Yes" and (not photo or not photo.filename):
            errors.append("Expired Items Photo is required when Expired Items = Yes.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("information/add_edit.html", mode="add", shops=shops_list, info=None)

        shop = get_shop(DB_PATH, int(shop_id))
        ensure_shop_folders(shop["name"])

        if photo and photo.filename:
            fn = secure_filename(photo.filename)
            dest = shop_folder(shop["name"]) / "exp_item" / f"expired_{int(datetime.utcnow().timestamp())}_{fn}"
            photo.save(dest)
            photo_rel = str(dest.relative_to(STATIC_DIR)).replace("\\", "/")

        info_id = create_info(
            DB_PATH, int(shop_id),
            ratings["clean"], ratings["management"], ratings["environment"], ratings["quality"],
            expired, int(expired_amount), photo_rel,
            other, other_message
        )

        if other == "Yes" and other_message:
            inspector = (session.get("user") or {}).get("username", "Unknown")
            write_other_message_txt(shop["name"], info_id, inspector, other_message)

        flash("Information saved", "success")
        return redirect(url_for("info_view", info_id=info_id))

    return render_template("information/add_edit.html", mode="add", shops=shops_list, info=None)


@app.get("/information/<int:info_id>")
@login_required
def info_view(info_id):
    info = get_info(DB_PATH, info_id)
    if not info:
        abort(404)
    shop = get_shop(DB_PATH, info["shop_id"])
    exp_items = list_exp_items(DB_PATH, info_id)
    return render_template("information/view.html", info=info, shop=shop, exp_items=exp_items)


@app.route("/information/<int:info_id>/edit", methods=["GET", "POST"])
@admin_required
def info_edit(info_id):
    info = get_info(DB_PATH, info_id)
    if not info:
        abort(404)
    shops_list = list_shops(DB_PATH)

    if request.method == "POST":
        old_shop = get_shop(DB_PATH, info["shop_id"])

        shop_id = request.form.get("shop_id")
        ratings = {
            "clean": request.form.get("clean"),
            "management": request.form.get("management"),
            "environment": request.form.get("environment"),
            "quality": request.form.get("quality"),
        }
        expired = request.form.get("expired")
        expired_amount = (request.form.get("expired_amount") or "").strip()
        other = request.form.get("other")
        other_message = (request.form.get("other_message") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        for k, v in ratings.items():
            if v not in {"Best", "Good", "Not Bad", "Super"}:
                errors.append(f"{k.title()} rating is required.")
        if expired not in {"Yes", "No"}:
            errors.append("Expired Items Yes/No is required.")
        if expired_amount == "":
            errors.append("Expired Items Amount is required (0 allowed).")
        else:
            try:
                int(expired_amount)
            except:
                errors.append("Expired Items Amount must be a number.")
        if other not in {"Yes", "No"}:
            errors.append("Other Yes/No is required.")
        if other == "Yes" and not other_message:
            errors.append("Other message is required when Other = Yes.")

        photo = request.files.get("expired_photo")
        photo_rel = info["expired_photo"]
        if photo and photo.filename:
            if not allowed_image(photo.filename):
                errors.append("Expired photo must be png/jpg/jpeg/webp.")
        if expired == "Yes" and (not photo_rel) and (not photo or not photo.filename):
            errors.append("Expired Items Photo is required when Expired Items = Yes.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("information/add_edit.html", mode="edit", shops=shops_list, info=info)

        new_shop = get_shop(DB_PATH, int(shop_id))
        ensure_shop_folders(new_shop["name"])

        if photo and photo.filename:
            fn = secure_filename(photo.filename)
            dest = shop_folder(new_shop["name"]) / "exp_item" / f"expired_{int(datetime.utcnow().timestamp())}_{fn}"
            photo.save(dest)
            photo_rel = str(dest.relative_to(STATIC_DIR)).replace("\\", "/")

        update_info(
            DB_PATH, info_id, int(shop_id),
            ratings["clean"], ratings["management"], ratings["environment"], ratings["quality"],
            expired, int(expired_amount), photo_rel,
            other, other_message
        )

        if old_shop and new_shop and old_shop["name"] != new_shop["name"]:
            delete_other_message_txt(old_shop["name"], info_id)

        if other == "Yes" and other_message:
            inspector = (session.get("user") or {}).get("username", "Unknown")
            write_other_message_txt(new_shop["name"], info_id, inspector, other_message)
        else:
            if old_shop:
                delete_other_message_txt(old_shop["name"], info_id)
            if new_shop:
                delete_other_message_txt(new_shop["name"], info_id)

        flash("Information updated", "success")
        return redirect(url_for("info_view", info_id=info_id))

    return render_template("information/add_edit.html", mode="edit", shops=shops_list, info=info)


@app.post("/information/<int:info_id>/delete")
@admin_required
def info_delete(info_id):
    info = get_info(DB_PATH, info_id)
    if info:
        shop = get_shop(DB_PATH, info["shop_id"])
        if shop:
            delete_other_message_txt(shop["name"], info_id)

    delete_info(DB_PATH, info_id)
    flash("Information deleted", "warning")
    return redirect(url_for("information"))


@app.post("/information/<int:info_id>/expired_photo/delete")
@admin_required
def expired_photo_delete(info_id):
    info = get_info(DB_PATH, info_id)
    if not info:
        abort(404)

    if info["expired_photo"]:
        pth = STATIC_DIR / info["expired_photo"]
        try:
            if pth.exists():
                pth.unlink()
        except:
            pass

    update_info(
        DB_PATH, info["id"], info["shop_id"],
        info["clean"], info["management"], info["environment"], info["quality"],
        info["expired"], info["expired_amount"], None,
        info["other"], info["other_message"]
    )
    flash("Expired photo removed", "info")
    return redirect(url_for("info_view", info_id=info["id"]))


# ---------------- Exp Items CRUD ----------------
@app.route("/information/<int:info_id>/exp/add", methods=["POST"])
@admin_required
def exp_add(info_id):
    name = (request.form.get("name") or "").strip()
    exp_d = (request.form.get("exp_d") or "").strip()
    mf_d = (request.form.get("mf_d") or "").strip()
    amount = (request.form.get("amount") or "").strip()
    price = (request.form.get("price") or "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not exp_d:
        errors.append("EXP.D is required.")
    if not mf_d:
        errors.append("MF.D is required.")
    if amount == "":
        errors.append("Amount is required.")
    if price == "":
        errors.append("Price is required.")

    try:
        int(amount)
    except:
        errors.append("Amount must be a number.")
    try:
        float(price)
    except:
        errors.append("Price must be a number.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("info_view", info_id=info_id))

    create_exp_item(DB_PATH, info_id, name, exp_d, mf_d, int(amount), float(price))
    flash("Expired item added", "success")
    return redirect(url_for("info_view", info_id=info_id))


@app.route("/exp/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def exp_edit(item_id):
    item = get_exp_item(DB_PATH, item_id)
    if not item:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        exp_d = (request.form.get("exp_d") or "").strip()
        mf_d = (request.form.get("mf_d") or "").strip()
        amount = (request.form.get("amount") or "").strip()
        price = (request.form.get("price") or "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not exp_d:
            errors.append("EXP.D is required.")
        if not mf_d:
            errors.append("MF.D is required.")

        try:
            int(amount)
        except:
            errors.append("Amount must be a number.")
        try:
            float(price)
        except:
            errors.append("Price must be a number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("information/exp_edit.html", item=item)

        update_exp_item(DB_PATH, item_id, name, exp_d, mf_d, int(amount), float(price))
        flash("Expired item updated", "success")
        return redirect(url_for("info_view", info_id=item["info_id"]))

    return render_template("information/exp_edit.html", item=item)


@app.post("/exp/<int:item_id>/delete")
@admin_required
def exp_delete(item_id):
    item = get_exp_item(DB_PATH, item_id)
    if not item:
        abort(404)
    delete_exp_item(DB_PATH, item_id)
    flash("Expired item deleted", "warning")
    return redirect(url_for("info_view", info_id=item["info_id"]))


# ---------------- Fast Items / Brands ----------------
@app.get("/fast-items")
@login_required
def fast_items():
    items = list_fast_items(DB_PATH)
    return render_template("fast_items/list.html", items=items)


@app.route("/fast-items/add", methods=["GET", "POST"])
@admin_required
def fast_items_add():
    shops_list = list_shops(DB_PATH)
    brands_list = list_brands(DB_PATH)

    if request.method == "POST":
        shop_id = request.form.get("shop_id")
        brand_id = request.form.get("brand_id")
        item_name = (request.form.get("item_name") or "").strip()
        discount = (request.form.get("discount") or "").strip()
        price = (request.form.get("price") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        if not brand_id:
            errors.append("Brand is required.")
        if not item_name:
            errors.append("Item Name is required.")
        if not discount:
            errors.append("Discount is required.")
        if price == "":
            errors.append("Price is required.")
        else:
            try:
                float(price)
            except:
                errors.append("Price must be a number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "fast_items/add_edit.html",
                mode="add",
                item=None,
                shops=shops_list,
                brands=brands_list
            )

        create_fast_item(DB_PATH, int(shop_id), int(brand_id), item_name, discount, float(price))
        flash("Fast item saved", "success")
        return redirect(url_for("fast_items"))

    return render_template(
        "fast_items/add_edit.html",
        mode="add",
        item=None,
        shops=shops_list,
        brands=brands_list
    )


@app.route("/fast-items/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def fast_items_edit(item_id):
    item = get_fast_item(DB_PATH, item_id)
    if not item:
        abort(404)

    shops_list = list_shops(DB_PATH)
    brands_list = list_brands(DB_PATH)

    if request.method == "POST":
        shop_id = request.form.get("shop_id")
        brand_id = request.form.get("brand_id")
        item_name = (request.form.get("item_name") or "").strip()
        discount = (request.form.get("discount") or "").strip()
        price = (request.form.get("price") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        if not brand_id:
            errors.append("Brand is required.")
        if not item_name:
            errors.append("Item Name is required.")
        if not discount:
            errors.append("Discount is required.")
        if price == "":
            errors.append("Price is required.")
        else:
            try:
                float(price)
            except:
                errors.append("Price must be a number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "fast_items/add_edit.html",
                mode="edit",
                item=item,
                shops=shops_list,
                brands=brands_list
            )

        update_fast_item(DB_PATH, item_id, int(shop_id), int(brand_id), item_name, discount, float(price))
        flash("Fast item updated", "success")
        return redirect(url_for("fast_items"))

    return render_template(
        "fast_items/add_edit.html",
        mode="edit",
        item=item,
        shops=shops_list,
        brands=brands_list
    )


@app.post("/fast-items/<int:item_id>/delete")
@admin_required
def fast_items_delete(item_id):
    delete_fast_item(DB_PATH, item_id)
    flash("Fast item deleted", "warning")
    return redirect(url_for("fast_items"))


@app.get("/fast-items/brands")
@login_required
def fast_items_brands():
    items = list_brands(DB_PATH)
    return render_template("fast_items/brands.html", brands=items)


@app.route("/fast-items/brands/add", methods=["GET", "POST"])
@admin_required
def fast_items_brand_add():
    if request.method == "POST":
        brand_name = (request.form.get("brand_name") or "").strip()

        if not brand_name:
            flash("Brand Name is required.", "danger")
            return render_template("fast_items/brand_add_edit.html", mode="add", brand=None)

        try:
            create_brand(DB_PATH, brand_name)
            flash("Brand saved", "success")
            return redirect(url_for("fast_items_brands"))
        except Exception:
            flash("Brand name already exists.", "danger")
            return render_template("fast_items/brand_add_edit.html", mode="add", brand=None)

    return render_template("fast_items/brand_add_edit.html", mode="add", brand=None)


@app.route("/fast-items/brands/<int:brand_id>/edit", methods=["GET", "POST"])
@admin_required
def fast_items_brand_edit(brand_id):
    brand = get_brand(DB_PATH, brand_id)
    if not brand:
        abort(404)

    if request.method == "POST":
        brand_name = (request.form.get("brand_name") or "").strip()

        if not brand_name:
            flash("Brand Name is required.", "danger")
            return render_template("fast_items/brand_add_edit.html", mode="edit", brand=brand)

        try:
            update_brand(DB_PATH, brand_id, brand_name)
            flash("Brand updated", "success")
            return redirect(url_for("fast_items_brands"))
        except Exception:
            flash("Brand name already exists.", "danger")
            return render_template("fast_items/brand_add_edit.html", mode="edit", brand=brand)

    return render_template("fast_items/brand_add_edit.html", mode="edit", brand=brand)


@app.post("/fast-items/brands/<int:brand_id>/delete")
@admin_required
def fast_items_brand_delete(brand_id):
    try:
        delete_brand(DB_PATH, brand_id)
        flash("Brand deleted", "warning")
    except Exception:
        flash("This brand is already used in Fast Items. Delete related Fast Items first.", "danger")
    return redirect(url_for("fast_items_brands"))


# ---------------- Contacts ----------------
@app.get("/contacts")
@login_required
def contacts():
    contacts_list = list_contacts(DB_PATH)
    return render_template("contacts/list.html", contacts=contacts_list)


@app.route("/contacts/add", methods=["GET", "POST"])
@admin_required
def contacts_add():
    shops_list = list_shops(DB_PATH)

    if request.method == "POST":
        shop_id = request.form.get("shop_id")
        manager_name = (request.form.get("manager_name") or "").strip()
        age = (request.form.get("age") or "").strip()
        address = (request.form.get("address") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        if not manager_name:
            errors.append("Manager Name is required.")
        if age == "":
            errors.append("Age is required.")
        else:
            try:
                int(age)
            except:
                errors.append("Age must be a number.")
        if not address:
            errors.append("Address is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("contacts/add_edit.html", mode="add", shops=shops_list, contact=None)

        create_contact(DB_PATH, int(shop_id), manager_name, int(age), address)
        flash("Contact saved", "success")
        return redirect(url_for("contacts"))

    return render_template("contacts/add_edit.html", mode="add", shops=shops_list, contact=None)


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
@admin_required
def contacts_edit(contact_id):
    shops_list = list_shops(DB_PATH)
    c = get_contact(DB_PATH, contact_id)
    if not c:
        abort(404)

    if request.method == "POST":
        shop_id = request.form.get("shop_id")
        manager_name = (request.form.get("manager_name") or "").strip()
        age = (request.form.get("age") or "").strip()
        address = (request.form.get("address") or "").strip()

        errors = []
        if not shop_id:
            errors.append("Shop is required.")
        if not manager_name:
            errors.append("Manager Name is required.")
        try:
            int(age)
        except:
            errors.append("Age must be a number.")
        if not address:
            errors.append("Address is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("contacts/add_edit.html", mode="edit", shops=shops_list, contact=c)

        update_contact(DB_PATH, contact_id, int(shop_id), manager_name, int(age), address)
        flash("Contact updated", "success")
        return redirect(url_for("contacts"))

    return render_template("contacts/add_edit.html", mode="edit", shops=shops_list, contact=c)


@app.post("/contacts/<int:contact_id>/delete")
@admin_required
def contacts_delete(contact_id):
    delete_contact(DB_PATH, contact_id)
    flash("Contact deleted", "warning")
    return redirect(url_for("contacts"))


# ---------------- PDF ----------------
@app.route("/pdf", methods=["GET", "POST"])
@login_required
def pdf_page():
    shops_list = list_shops(DB_PATH)
    selected_shop_id = request.form.get("shop_id") if request.method == "POST" else request.args.get("shop_id")
    selected_date = request.form.get("date_key") if request.method == "POST" else request.args.get("date_key")

    dates = []
    if selected_shop_id:
        dates = list_info_dates_for_shop(DB_PATH, int(selected_shop_id))

    return render_template(
        "pdf/page.html",
        shops=shops_list,
        dates=dates,
        selected_shop_id=selected_shop_id,
        selected_date=selected_date
    )


@app.get("/pdf/download/expired")
@login_required
def pdf_download_expired():
    shop_id = request.args.get("shop_id", type=int)
    date_key = request.args.get("date_key", type=str)

    if not shop_id or not date_key:
        flash("Select Shop and Date", "danger")
        return redirect(url_for("pdf_page"))

    info_id = int(date_key)
    info = get_info(DB_PATH, info_id)
    if not info or info["shop_id"] != shop_id:
        abort(404)

    shop = get_shop(DB_PATH, shop_id)
    items = list_exp_items(DB_PATH, info_id)

    out_dir = APP_DIR / "generated_pdfs"
    out_dir.mkdir(exist_ok=True)

    filename = f"{slugify(shop['name'])}_expired_{info['created_at'].replace(':','-').replace(' ','_')}.pdf"
    out_path = out_dir / filename

    build_exp_items_pdf(out_path, shop["name"], info["created_at"], items)
    return send_file(out_path, as_attachment=True, download_name=filename)


@app.get("/pdf/download/fast-items")
@login_required
def pdf_download_fast_items():
    shop_id = request.args.get("shop_id", type=int)
    date_key = request.args.get("date_key", type=str)

    if not shop_id or not date_key:
        flash("Select Shop and Date", "danger")
        return redirect(url_for("pdf_page"))

    info_id = int(date_key)
    info = get_info(DB_PATH, info_id)
    if not info or info["shop_id"] != shop_id:
        abort(404)

    shop = get_shop(DB_PATH, shop_id)
    if not shop:
        abort(404)

    created_date = created_date_only(info["created_at"])
    created_time = created_time_only(info["created_at"])

    fast_items_rows = list_fast_items_for_shop_and_date(DB_PATH, shop_id, created_date)
    inspector = (session.get("user") or {}).get("username", "Unknown")
    message = info.get("other_message") if info.get("other") == "Yes" else ""

    out_dir = APP_DIR / "generated_pdfs"
    out_dir.mkdir(exist_ok=True)

    filename = f"{slugify(shop['name'])}_fast_items_{info['created_at'].replace(':','-').replace(' ','_')}.pdf"
    out_path = out_dir / filename

    build_fast_items_pdf(
        out_path=out_path,
        shop_name=shop["name"],
        date_str=created_date,
        time_str=created_time,
        inspector=inspector,
        fast_items=fast_items_rows,
        message=message or ""
    )
    return send_file(out_path, as_attachment=True, download_name=filename)


if __name__ == "__main__":
import os
port = int(os.environ.get("PORT,5000))
    app.run(host="0.0.0.0", port=port)