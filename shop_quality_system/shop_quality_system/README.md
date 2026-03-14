# Shop Quality + Expired Items System (Flask + SQLite)

## Install & Run
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:
- http://127.0.0.1:5000

## First Admin (one-time)
If there are no users in the database, you can create the first admin by setting environment variables before running:
- FIRST_ADMIN_USER
- FIRST_ADMIN_PASS

(These values are never displayed in the UI.)

## Phone Access (Free, no domain)
On the office PC:
```bash
cloudflared tunnel --url http://localhost:5000
```
Open the generated `trycloudflare.com` link on your phone.
