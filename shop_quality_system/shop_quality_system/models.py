import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','user'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        location TEXT NOT NULL,
        shop_type TEXT NOT NULL CHECK(shop_type IN ('Co-Op','Mini Co-Op','Regional')),
        pos_system TEXT NOT NULL CHECK(pos_system IN ('Yes','No')),
        shop_photo TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS information (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER NOT NULL,
        clean TEXT NOT NULL CHECK(clean IN ('Best','Good','Not Bad','Super')),
        management TEXT NOT NULL CHECK(management IN ('Best','Good','Not Bad','Super')),
        environment TEXT NOT NULL CHECK(environment IN ('Best','Good','Not Bad','Super')),
        quality TEXT NOT NULL CHECK(quality IN ('Best','Good','Not Bad','Super')),
        expired TEXT NOT NULL CHECK(expired IN ('Yes','No')),
        expired_amount INTEGER NOT NULL,
        expired_photo TEXT,
        other TEXT NOT NULL CHECK(other IN ('Yes','No')),
        other_message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(shop_id) REFERENCES shops(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exp_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        info_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        exp_d TEXT NOT NULL,
        mf_d TEXT NOT NULL,
        amount INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(info_id) REFERENCES information(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER NOT NULL,
        manager_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        address TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(shop_id) REFERENCES shops(id) ON DELETE CASCADE
    );
    """)

    # ✅ NEW: brands
    cur.execute("""
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_name TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # ✅ NEW: fast_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fast_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER NOT NULL,
        brand_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        discount TEXT NOT NULL,
        price REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(shop_id) REFERENCES shops(id) ON DELETE CASCADE,
        FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE RESTRICT
    );
    """)

    conn.commit()
    conn.close()


# ---------------- Users ----------------
def ensure_first_admin(db_path: str, username: str, password: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users;")
    c = cur.fetchone()["c"]
    if c == 0:
        cur.execute(
            "INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
            (username, generate_password_hash(password), "admin")
        )
        conn.commit()
    conn.close()


def create_user(db_path: str, username: str, password: str, role: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
        (username, generate_password_hash(password), role)
    )
    conn.commit()
    conn.close()


def get_user_by_username(db_path: str, username: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?;", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def verify_password(password: str, password_hash: str) -> bool:
    # ✅ FIXED
    return check_password_hash(password_hash, password)


# ---------------- Shops ----------------
def list_shops(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM shops ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shop(db_path: str, shop_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM shops WHERE id=?;", (shop_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_shop(db_path: str, name: str, location: str, shop_type: str, pos_system: str, shop_photo: str | None):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shops (name, location, shop_type, pos_system, shop_photo, created_at)
        VALUES (?,?,?,?,?,?);
    """, (name, location, shop_type, pos_system, shop_photo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def update_shop(db_path: str, shop_id: int, name: str, location: str, shop_type: str, pos_system: str, shop_photo: str | None):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE shops SET name=?, location=?, shop_type=?, pos_system=?, shop_photo=?
        WHERE id=?;
    """, (name, location, shop_type, pos_system, shop_photo, shop_id))
    conn.commit()
    conn.close()


def delete_shop(db_path: str, shop_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM shops WHERE id=?;", (shop_id,))
    conn.commit()
    conn.close()


# ---------------- Information ----------------
def list_info_summaries(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT information.id AS id, information.shop_id AS shop_id, shops.name AS shop_name, information.created_at AS created_at
        FROM information
        JOIN shops ON shops.id = information.shop_id
        ORDER BY information.id DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_info_dates_for_shop(db_path: str, shop_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at FROM information
        WHERE shop_id=?
        ORDER BY id DESC;
    """, (shop_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_info(db_path: str, info_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM information WHERE id=?;", (info_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_info(db_path: str, shop_id: int,
                clean: str, management: str, environment: str, quality: str,
                expired: str, expired_amount: int, expired_photo: str | None,
                other: str, other_message: str | None):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO information (
            shop_id, clean, management, environment, quality,
            expired, expired_amount, expired_photo,
            other, other_message, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?);
    """, (
        shop_id, clean, management, environment, quality,
        expired, expired_amount, expired_photo,
        other, other_message,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    info_id = cur.lastrowid
    conn.commit()
    conn.close()
    return info_id


def update_info(db_path: str, info_id: int, shop_id: int,
                clean: str, management: str, environment: str, quality: str,
                expired: str, expired_amount: int, expired_photo: str | None,
                other: str, other_message: str | None):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE information SET
            shop_id=?, clean=?, management=?, environment=?, quality=?,
            expired=?, expired_amount=?, expired_photo=?,
            other=?, other_message=?
        WHERE id=?;
    """, (
        shop_id, clean, management, environment, quality,
        expired, expired_amount, expired_photo,
        other, other_message,
        info_id
    ))
    conn.commit()
    conn.close()


def delete_info(db_path: str, info_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM information WHERE id=?;", (info_id,))
    conn.commit()
    conn.close()


# ---------------- Exp Items ----------------
def list_exp_items(db_path: str, info_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM exp_items WHERE info_id=? ORDER BY id DESC;", (info_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def create_exp_item(db_path: str, info_id: int, name: str, exp_d: str, mf_d: str, amount: int, price: float):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exp_items (info_id, name, exp_d, mf_d, amount, price)
        VALUES (?,?,?,?,?,?);
    """, (info_id, name, exp_d, mf_d, amount, price))
    conn.commit()
    conn.close()


def get_exp_item(db_path: str, item_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM exp_items WHERE id=?;", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_exp_item(db_path: str, item_id: int, name: str, exp_d: str, mf_d: str, amount: int, price: float):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE exp_items SET name=?, exp_d=?, mf_d=?, amount=?, price=? WHERE id=?;
    """, (name, exp_d, mf_d, amount, price, item_id))
    conn.commit()
    conn.close()


def delete_exp_item(db_path: str, item_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM exp_items WHERE id=?;", (item_id,))
    conn.commit()
    conn.close()


# ---------------- Contacts ----------------
def list_contacts(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT contacts.*, shops.name AS shop_name
        FROM contacts JOIN shops ON shops.id = contacts.shop_id
        ORDER BY contacts.id DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_contact(db_path: str, contact_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE id=?;", (contact_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_contact(db_path: str, shop_id: int, manager_name: str, age: int, address: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contacts (shop_id, manager_name, age, address, created_at)
        VALUES (?,?,?,?,?);
    """, (shop_id, manager_name, age, address, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def update_contact(db_path: str, contact_id: int, shop_id: int, manager_name: str, age: int, address: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE contacts SET shop_id=?, manager_name=?, age=?, address=? WHERE id=?;
    """, (shop_id, manager_name, age, address, contact_id))
    conn.commit()
    conn.close()


def delete_contact(db_path: str, contact_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id=?;", (contact_id,))
    conn.commit()
    conn.close()


# ---------------- Brands ----------------
def list_brands(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM brands ORDER BY brand_name;")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_brand(db_path: str, brand_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM brands WHERE id=?;", (brand_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_brand(db_path: str, brand_name: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO brands (brand_name, created_at)
        VALUES (?,?);
    """, (brand_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def update_brand(db_path: str, brand_id: int, brand_name: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE brands SET brand_name=? WHERE id=?;
    """, (brand_name, brand_id))
    conn.commit()
    conn.close()


def delete_brand(db_path: str, brand_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM brands WHERE id=?;", (brand_id,))
    conn.commit()
    conn.close()


# ---------------- Fast Items ----------------
def list_fast_items(db_path: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            fi.*,
            s.name AS shop_name,
            b.brand_name AS brand_name
        FROM fast_items fi
        JOIN shops s ON s.id = fi.shop_id
        JOIN brands b ON b.id = fi.brand_id
        ORDER BY fi.id DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_fast_item(db_path: str, item_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM fast_items WHERE id=?;", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_fast_item(db_path: str, shop_id: int, brand_id: int, item_name: str, discount: str, price: float):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO fast_items (shop_id, brand_id, item_name, discount, price, created_at)
        VALUES (?,?,?,?,?,?);
    """, (
        shop_id, brand_id, item_name, discount, price,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def update_fast_item(db_path: str, item_id: int, shop_id: int, brand_id: int, item_name: str, discount: str, price: float):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE fast_items SET
            shop_id=?, brand_id=?, item_name=?, discount=?, price=?
        WHERE id=?;
    """, (shop_id, brand_id, item_name, discount, price, item_id))
    conn.commit()
    conn.close()


def delete_fast_item(db_path: str, item_id: int):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM fast_items WHERE id=?;", (item_id,))
    conn.commit()
    conn.close()


def list_fast_items_for_shop_and_date(db_path: str, shop_id: int, date_str: str):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            fi.*,
            s.name AS shop_name,
            b.brand_name AS brand_name
        FROM fast_items fi
        JOIN shops s ON s.id = fi.shop_id
        JOIN brands b ON b.id = fi.brand_id
        WHERE fi.shop_id = ?
          AND substr(fi.created_at, 1, 10) = ?
        ORDER BY fi.id ASC;
    """, (shop_id, date_str))
    rows = cur.fetchall()
    conn.close()
    return rows