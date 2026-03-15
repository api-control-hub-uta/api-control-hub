from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sqlite3

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "smart_closet.db"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# HOME PAGE
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users LIMIT 5")
    profiles = cur.fetchall()

    conn.close()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "profiles": profiles
        }
    )


# MANAGE PROFILES PAGE
@app.get("/profiles", response_class=HTMLResponse)
def manage_profiles(request: Request):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users LIMIT 5")
    profiles = cur.fetchall()

    conn.close()

    return templates.TemplateResponse(
        "manage_profiles.html",
        {
            "request": request,
            "profiles": profiles
        }
    )


# CREATE PROFILE PAGE
@app.get("/profiles/new", response_class=HTMLResponse)
def create_profile_page(request: Request):
    return templates.TemplateResponse("create_profile.html", {"request": request})


# SAVE NEW PROFILE
@app.post("/profiles/new")
def save_profile(name: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("INSERT INTO users (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/", status_code=303)


# EDIT PROFILE PAGE
@app.get("/profiles/edit/{profile_id}", response_class=HTMLResponse)
def edit_profile_page(profile_id: int, request: Request):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    conn.close()

    return templates.TemplateResponse(
        "edit_profile.html",
        {
            "request": request,
            "profile": profile
        }
    )


# SAVE EDITED PROFILE
@app.post("/profiles/edit/{profile_id}")
def update_profile(profile_id: int, name: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("UPDATE users SET name = ? WHERE id = ?", (name, profile_id))

    conn.commit()
    conn.close()

    return RedirectResponse(url="/profiles", status_code=303)


# DELETE PROFILE
@app.post("/profiles/delete/{profile_id}")
def delete_profile(profile_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM preferences WHERE user_id = ?", (profile_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (profile_id,))

    conn.commit()
    conn.close()

    return RedirectResponse(url="/profiles", status_code=303)


# LOCK PROFILE PLACEHOLDER
@app.get("/profiles/lock/{profile_id}", response_class=HTMLResponse)
def lock_profile(profile_id: int):
    return f"""
    <h1>Lock Profile {profile_id}</h1>
    <p>This feature will be built next.</p>
    <a href="/profiles">Go Back</a>
    """


# UPLOAD IMAGE PLACEHOLDER
@app.get("/profiles/upload/{profile_id}", response_class=HTMLResponse)
def upload_profile_image(profile_id: int):
    return f"""
    <h1>Upload Image for Profile {profile_id}</h1>
    <p>This feature will be built later.</p>
    <a href="/profiles">Go Back</a>
    """


# SETTINGS PAGE
@app.get("/settings", response_class=HTMLResponse)
def settings():
    return """
    <h1>Settings Page</h1>
    <p>This page will be built later.</p>
    <a href="/">Go Back</a>
    """


# DASHBOARD PAGE
@app.get("/dashboard/{profile_id}", response_class=HTMLResponse)
def dashboard(profile_id: int, request: Request):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    conn.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profile": profile
        }
    )


# PREFERENCES PLACEHOLDER
@app.get("/preferences/{profile_id}", response_class=HTMLResponse)
def preferences_page(profile_id: int, request: Request):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    conn.close()

    return templates.TemplateResponse(
        "preferences.html",
        {
            "request": request,
            "profile": profile
        }
    )


@app.post("/preferences/{profile_id}")
def save_preferences(
    profile_id: int,
    hot_threshold: int = Form(...),
    moderate_threshold: int = Form(...),
    cold_threshold: int = Form(...),
    extreme_cold_threshold: int = Form(...),
    hot_clothing: str = Form(...),
    moderate_clothing: str = Form(...),
    cold_clothing: str = Form(...),
    extreme_cold_clothing: str = Form(...)
):
    print("Using database:", DB_PATH)   
    conn =sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM preferences WHERE user_id = ?", (profile_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE preferences
            SET hot_threshold = ?,
                moderate_threshold = ?,
                cold_threshold = ?,
                extreme_cold_threshold = ?,
                hot_clothing = ?,
                moderate_clothing = ?,
                cold_clothing = ?,
                extreme_cold_clothing = ?
            WHERE user_id = ?
        """, (
            hot_threshold,
            moderate_threshold,
            cold_threshold,
            extreme_cold_threshold,
            hot_clothing,
            moderate_clothing,
            cold_clothing,
            extreme_cold_clothing,
            profile_id
        ))
    else:
        cur.execute("""
            INSERT INTO preferences (
                user_id,
                hot_threshold,
                moderate_threshold,
                cold_threshold,
                extreme_cold_threshold,
                hot_clothing,
                moderate_clothing,
                cold_clothing,
                extreme_cold_clothing
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            hot_threshold,
            moderate_threshold,
            cold_threshold,
            extreme_cold_threshold,
            hot_clothing,
            moderate_clothing,
            cold_clothing,
            extreme_cold_clothing
        ))

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/dashboard/{profile_id}", status_code=303)

# RECOMMENDATION PLACEHOLDER
@app.get("/recommendation/{profile_id}", response_class=HTMLResponse)
def recommendation(profile_id: int):
    return f"""
    <h1>Recommendation Page for Profile {profile_id}</h1>
    <p>This page will be built later.</p>
    <a href="/">Go Back</a>
    """

@app.get("/debug-db")
def debug_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(preferences)")
    columns = cur.fetchall()

    conn.close()
    return {"db_path": str(DB_PATH), "columns": columns}