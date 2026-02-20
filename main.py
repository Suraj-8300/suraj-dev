"""
Suraj's Portfolio — FastAPI Backend
Run locally:  uvicorn main:app --reload
Deploy:       Vercel (see vercel.json)

Storage: Supabase (persistent PostgreSQL — free tier, unlimited reads/writes)
  Set these in Vercel environment variables:
    SUPABASE_URL      → your project URL  e.g. https://xxxx.supabase.co
    SUPABASE_KEY      → your anon/service_role key
  Falls back to local data/site.json for local dev if not set.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional
from datetime import datetime

current_year = datetime.now().year

# ── App setup ──────────────────────────────────────────────────────────────
app = FastAPI(title="Suraj Portfolio")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATA_FILE      = Path("data/site.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# We store the whole site JSON as a single row in a table called `site_data`
# Schema (run once in Supabase SQL editor):
#
#   create table site_data (
#     id   int primary key default 1,
#     data jsonb not null
#   );
#   insert into site_data (id, data) values (1, '{}'::jsonb);
#
TABLE = "site_data"


# ── Supabase REST helpers (no SDK needed — plain HTTP) ─────────────────────
def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def load_data() -> dict:
    """Load site data — from Supabase if configured, else local file (dev)."""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.1&select=data"
            req = urllib.request.Request(url, headers=_sb_headers())
            with urllib.request.urlopen(req, timeout=8) as resp:
                rows = json.loads(resp.read().decode())
                if rows:
                    return rows[0]["data"]
        except Exception as e:
            print(f"Supabase read error: {e} — falling back to local file")
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_data(data: dict):
    """Save site data — to Supabase if configured, else local file (dev)."""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            payload = json.dumps({"id": 1, "data": data}).encode()
            url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.1"
            req = urllib.request.Request(url, data=payload, method="PATCH", headers=_sb_headers())
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp.read()
            return
        except Exception as e:
            print(f"Supabase write error: {e} — falling back to local file")
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Models ─────────────────────────────────────────────────────────────────
class ContactForm(BaseModel):
    name: str
    email: str
    subject: Optional[str] = "Portfolio Contact"
    message: str


class AdminLogin(BaseModel):
    password: str


class SiteData(BaseModel):
    meta: dict
    hero: dict
    about: dict
    skills: list
    projects: list
    social: dict


# ── Frontend routes ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    data = load_data()
    return templates.TemplateResponse("index.html", {"request": request, **data})


@app.get("/adminaccess", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


# ── API routes ──────────────────────────────────────────────────────────────
@app.post("/api/contact")
async def contact(form: ContactForm):
    """Send contact form email via Gmail SMTP"""
    name    = form.name.strip()
    email   = form.email.strip()
    subject = (form.subject or "Portfolio Contact").strip()
    message = form.message.strip()

    if not name or not email or not message:
        raise HTTPException(400, "Name, email and message are required.")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address.")

    smtp_user = os.environ.get("CONTACT_EMAIL", "")
    smtp_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_email  = os.environ.get("TO_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        print(f"\n📬 Contact form:\nFrom: {name} <{email}>\nSubject: {subject}\n{message}\n")
        return {"success": True, "message": "Message received! (Dev mode — email not sent)"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"]  = f"[Portfolio] {subject}"
        msg["From"]     = smtp_user
        msg["To"]       = to_email
        msg["Reply-To"] = email

        plain = f"From: {name} <{email}>\n\n{message}"
        html  = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
          <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px;border-radius:12px 12px 0 0;text-align:center">
            <h2 style="color:white;margin:0">📬 New Portfolio Message</h2>
          </div>
          <div style="background:#f8fafc;padding:28px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0">
            <p style="margin:0 0 8px"><b>From:</b> {name} &lt;{email}&gt;</p>
            <p style="margin:0 0 20px"><b>Subject:</b> {subject}</p>
            <div style="background:white;padding:16px;border-radius:8px;border-left:4px solid #6366f1;white-space:pre-wrap">{message}</div>
            <div style="margin-top:24px;text-align:center">
              <a href="mailto:{email}" style="background:#6366f1;color:white;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600">Reply to {name}</a>
            </div>
          </div>
        </div>"""

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        return {"success": True, "message": "Message sent!"}

    except Exception as e:
        print(f"Email error: {e}")
        raise HTTPException(500, "Failed to send email. Please try again.")


@app.post("/api/admin/login")
async def admin_login(body: AdminLogin):
    """Verify admin password and return a simple token"""
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Wrong password.")
    import hashlib
    token = hashlib.sha256(body.password.encode()).hexdigest()
    return {"success": True, "token": token}


def verify_admin(request: Request):
    """Dependency — checks X-Admin-Token header"""
    import hashlib
    token    = request.headers.get("X-Admin-Token", "")
    expected = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    if token != expected:
        raise HTTPException(403, "Unauthorized.")


@app.get("/api/admin/data")
async def get_data(_: None = Depends(verify_admin)):
    """Return full site data to admin panel"""
    return load_data()


@app.post("/api/admin/save")
async def save_site_data(data: SiteData, _: None = Depends(verify_admin)):
    """Save updated site data — persists instantly via Supabase"""
    save_data(data.model_dump())
    return {"success": True, "message": "Saved! Changes are live instantly."}
