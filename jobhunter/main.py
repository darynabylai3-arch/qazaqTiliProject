from fastapi import FastAPI, Request, Form, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
import os
import time

app = FastAPI(title="JobHunter")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = "db.json"


def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "users": {
                "admin": {"password": "admin", "role": "admin"},
                "user": {"password": "user", "role": "user"}
            },
            "jobs": [],
            "applications": []
        }

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=2, ensure_ascii=False)

        return default_db

    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def get_current_user(session: Optional[str] = Cookie(default=None)):
    if not session:
        return None

    db = load_db()

    if session in db["users"]:
        return {
            "username": session,
            **db["users"][session]
        }

    return None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Optional[str] = Cookie(default=None)):
    user = get_current_user(session)
    db = load_db()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "jobs": list(reversed(db["jobs"])),
        "applications": db["applications"]
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    db = load_db()

    if username in db["users"] and db["users"][username]["password"] == password:
        response = RedirectResponse("/", status_code=302)
        response.set_cookie("session", username, httponly=True)
        return response

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Неверный логин или пароль"
    })


@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session")
    return response


@app.post("/jobs/create")
async def create_job(
    title: str = Form(...),
    company: str = Form(...),
    description: str = Form(...),
    salary_min: int = Form(...),
    salary_max: int = Form(...),
    language: str = Form(...),
    is_internship: bool = Form(False),
    location: str = Form(...),
    session: Optional[str] = Cookie(default=None)
):
    user = get_current_user(session)

    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403)

    db = load_db()

    job = {
        "id": int(time.time() * 1000),
        "title": title,
        "company": company,
        "description": description,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "language": language,
        "is_internship": is_internship,
        "location": location,
        "created_by": session,
        "created_at": time.strftime("%Y-%m-%d")
    }

    db["jobs"].append(job)
    save_db(db)

    return RedirectResponse("/", status_code=302)


@app.post("/jobs/{job_id}/apply")
async def apply_job(
    job_id: int,
    skill_level: str = Form(...),
    cover_letter: str = Form(...),
    session: Optional[str] = Cookie(default=None)
):
    user = get_current_user(session)

    if not user or user["role"] != "user":
        raise HTTPException(status_code=403)

    db = load_db()

    for application in db["applications"]:
        if application["job_id"] == job_id and application["username"] == session:
            return RedirectResponse("/?error=already_applied", status_code=302)

    application = {
        "id": int(time.time() * 1000),
        "job_id": job_id,
        "username": session,
        "skill_level": skill_level,
        "cover_letter": cover_letter,
        "status": "pending",
        "applied_at": time.strftime("%Y-%m-%d")
    }

    db["applications"].append(application)
    save_db(db)

    return RedirectResponse("/", status_code=302)


@app.get("/admin/applications", response_class=HTMLResponse)
async def admin_applications(
    request: Request,
    session: Optional[str] = Cookie(default=None)
):
    user = get_current_user(session)

    if not user or user["role"] != "admin":
        return RedirectResponse("/login")

    db = load_db()

    enriched = []

    for application in db["applications"]:
        job = next(
            (j for j in db["jobs"] if j["id"] == application["job_id"]),
            None
        )

        enriched.append({
            **application,
            "job": job
        })

    return templates.TemplateResponse("applications.html", {
        "request": request,
        "user": user,
        "applications": list(reversed(enriched))
    })


@app.post("/admin/applications/{app_id}/status")
async def update_status(
    app_id: int,
    status: str = Form(...),
    session: Optional[str] = Cookie(default=None)
):
    user = get_current_user(session)

    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403)

    db = load_db()

    for application in db["applications"]:
        if application["id"] == app_id:
            application["status"] = status
            break

    save_db(db)

    return RedirectResponse("/admin/applications", status_code=302)


@app.get("/my/applications", response_class=HTMLResponse)
async def my_applications(
    request: Request,
    session: Optional[str] = Cookie(default=None)
):
    user = get_current_user(session)

    if not user or user["role"] != "user":
        return RedirectResponse("/login")

    db = load_db()

    enriched = []

    for application in db["applications"]:
        if application["username"] == session:
            job = next(
                (j for j in db["jobs"] if j["id"] == application["job_id"]),
                None
            )

            enriched.append({
                **application,
                "job": job
            })

    return templates.TemplateResponse("my_applications.html", {
        "request": request,
        "user": user,
        "applications": list(reversed(enriched))
    })