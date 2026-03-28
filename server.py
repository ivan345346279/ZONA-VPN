import os
import json
import hmac
import hashlib
import time
import sqlite3
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash, g)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production-super-secret")

@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return json.loads(value) if isinstance(value, str) else (value or [])
    except Exception:
        return []

BOT_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "8665930056:AAEOAuUKw5rEj7-8Lk1VvepkafWiL7p5NRM")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "[eoahirujgvE;AOJETHJKUKRL1223413568466]")
DATABASE       = os.path.join(BASE_DIR, "vpn.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE, username TEXT,
            first_name TEXT, last_name TEXT, photo_url TEXT,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, price REAL NOT NULL,
            period TEXT NOT NULL DEFAULT 'month',
            currency TEXT NOT NULL DEFAULT 'RUB',
            devices INTEGER DEFAULT 1,
            speed TEXT DEFAULT 'Без ограничений',
            features TEXT DEFAULT '[]',
            is_popular INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
    """)
    if db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0:
        plans = [
            ("Старт",0,"month","RUB",1,"До 50 Мбит/с",
             json.dumps(["1 устройство","Пробный 7 дней","Базовые серверы"],ensure_ascii=False),0,1,1),
            ("Базовый",249,"month","RUB",3,"До 150 Мбит/с",
             json.dumps(["3 устройства","20+ серверов","Без логов","Поддержка 24/7"],ensure_ascii=False),0,1,2),
            ("Про",449,"month","RUB",5,"Без ограничений",
             json.dumps(["5 устройств","50+ серверов","Без логов","Приоритетная поддержка","Kill Switch"],ensure_ascii=False),1,1,3),
            ("Семейный",749,"month","RUB",10,"Без ограничений",
             json.dumps(["10 устройств","Все серверы","Без логов","VIP поддержка","Выделенный IP"],ensure_ascii=False),0,1,4),
        ]
        db.executemany(
            "INSERT INTO plans (name,price,period,currency,devices,speed,features,is_popular,is_active,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
            plans
        )
    defaults = {
        "site_name":"NordShield VPN","hero_title":"Ваша защита в сети",
        "hero_subtitle":"Быстрый, надёжный и безопасный VPN-сервис. Подключитесь за 1 клик.",
        "hero_badge":"Более 50 000 пользователей",
        "primary_color":"#6C63FF","accent_color":"#00D4FF",
        "bot_username":"","bot_token":"",
    }
    for k, v in defaults.items():
        db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",(k,v))
    db.commit()
    db.close()

def get_settings():
    rows = get_db().execute("SELECT key,value FROM site_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}

def get_bot_token():
    return BOT_TOKEN or (get_settings().get("bot_token") or "")

def verify_telegram_auth(data: dict) -> bool:
    token = get_bot_token()
    if not token:
        return True  # demo-mode
    received_hash = data.get("hash","")
    auth_date     = int(data.get("auth_date",0))
    if time.time() - auth_date > 86400:
        return False
    check_fields = {k:v for k,v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k,v in sorted(check_fields.items()))
    secret   = hashlib.sha256(token.encode()).digest()
    computed = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, received_hash)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index", login=1))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    plans    = get_db().execute("SELECT * FROM plans WHERE is_active=1 ORDER BY sort_order").fetchall()
    settings = get_settings()
    user = get_db().execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone() if "user_id" in session else None
    return render_template("index.html", plans=plans, settings=settings, user=user)

@app.route("/pricing")
def pricing():
    plans    = get_db().execute("SELECT * FROM plans WHERE is_active=1 ORDER BY sort_order").fetchall()
    settings = get_settings()
    user = get_db().execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone() if "user_id" in session else None
    return render_template("pricing.html", plans=plans, settings=settings, user=user)

@app.route("/telegram-login", methods=["POST"])
def telegram_login():
    data = request.json or {}
    if not data.get("id"):
        return jsonify({"ok":False,"error":"no_data"}),400
    if not verify_telegram_auth(dict(data)):
        return jsonify({"ok":False,"error":"invalid_hash"}),403
    tg_id = int(data["id"])
    db    = get_db()
    db.execute("""
        INSERT INTO users (tg_id,username,first_name,last_name,photo_url)
        VALUES (?,?,?,?,?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username=excluded.username, first_name=excluded.first_name,
            last_name=excluded.last_name, photo_url=excluded.photo_url
    """, (tg_id, data.get("username",""), data.get("first_name",""),
          data.get("last_name",""), data.get("photo_url","")))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE tg_id=?",(tg_id,)).fetchone()
    session["user_id"]   = user["id"]
    session["user_name"] = data.get("first_name","User")
    return jsonify({"ok":True,"name":data.get("first_name","User"),"photo":data.get("photo_url","")})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Неверный пароль")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin",None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    plans       = db.execute("SELECT * FROM plans ORDER BY sort_order").fetchall()
    users_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    settings    = get_settings()
    return render_template("admin.html", plans=plans, users_count=users_count, settings=settings)

@app.route("/admin/plans/add", methods=["POST"])
@admin_required
def admin_add_plan():
    d = request.form
    features = [f.strip() for f in d.get("features","").split("\n") if f.strip()]
    get_db().execute(
        "INSERT INTO plans (name,price,period,currency,devices,speed,features,is_popular,is_active,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (d["name"],float(d["price"]),d.get("period","month"),d.get("currency","RUB"),
         int(d.get("devices",1)),d.get("speed","Без ограничений"),
         json.dumps(features,ensure_ascii=False),
         1 if d.get("is_popular") else 0, 1 if d.get("is_active") else 0,
         int(d.get("sort_order",0)))
    )
    get_db().commit()
    flash("Тариф добавлен!")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/plans/edit/<int:pid>", methods=["POST"])
@admin_required
def admin_edit_plan(pid):
    d = request.form
    features = [f.strip() for f in d.get("features","").split("\n") if f.strip()]
    get_db().execute(
        "UPDATE plans SET name=?,price=?,period=?,currency=?,devices=?,speed=?,features=?,is_popular=?,is_active=?,sort_order=? WHERE id=?",
        (d["name"],float(d["price"]),d.get("period","month"),d.get("currency","RUB"),
         int(d.get("devices",1)),d.get("speed","Без ограничений"),
         json.dumps(features,ensure_ascii=False),
         1 if d.get("is_popular") else 0, 1 if d.get("is_active") else 0,
         int(d.get("sort_order",0)), pid)
    )
    get_db().commit()
    flash("Тариф обновлён!")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/plans/delete/<int:pid>", methods=["POST"])
@admin_required
def admin_delete_plan(pid):
    get_db().execute("DELETE FROM plans WHERE id=?",(pid,))
    get_db().commit()
    flash("Тариф удалён!")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/settings", methods=["POST"])
@admin_required
def admin_settings():
    for key in ["site_name","hero_title","hero_subtitle","hero_badge","primary_color","accent_color","bot_username","bot_token"]:
        val = request.form.get(key)
        if val is not None:
            get_db().execute("INSERT OR REPLACE INTO site_settings (key,value) VALUES (?,?)",(key,val))
    get_db().commit()
    flash("Настройки сохранены!")
    return redirect(url_for("admin_dashboard"))

@app.route("/api/plans")
def api_plans():
    plans  = get_db().execute("SELECT * FROM plans WHERE is_active=1 ORDER BY sort_order").fetchall()
    result = []
    for p in plans:
        d = dict(p); d["features"] = json.loads(d["features"]); result.append(d)
    return jsonify(result)

if __name__ == "__main__":
    init_db()
    demo = not get_bot_token()
    print("="*50)
    print("🛡️  VPN Site  →  http://localhost:5000")
    print("⚙️  Admin     →  http://localhost:5000/admin")
    print(f"🔑 Пароль    →  {ADMIN_PASSWORD}")
    print("⚠️  Telegram demo" if demo else "✅  Telegram widget активен")
    print("="*50)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
