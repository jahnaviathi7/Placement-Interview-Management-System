
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import os

import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pydantic import BaseModel


# =========================================================
# CONFIGURATION
# =========================================================

BASE = Path(__file__).resolve().parent
DB = BASE / "placement.db"

SECRET = os.getenv(
    "SECRET_KEY",
    "placementhub-production-secret-change-this"
)

ALGORITHM = "HS256"


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Placement & Interview Management API",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    ""
).strip().rstrip("/")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# AUTHENTICATION
# =========================================================

oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/login"
)


# =========================================================
# DATABASE
# =========================================================

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def add_column_if_missing(
    con,
    table,
    column,
    definition
):
    columns = [
        row["name"]
        for row in con.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]

    if column not in columns:
        con.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_db():
    con = db()

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            posted_by INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Applied'
        );

        CREATE TABLE IF NOT EXISTS interviews(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            interview_date TEXT NOT NULL,
            interviewer TEXT NOT NULL,
            mode TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT 'Pending'
        );
        """
    )

    # Add newer interview columns if an older database already exists.
    add_column_if_missing(
        con,
        "interviews",
        "meeting_link",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        con,
        "interviews",
        "notes",
        "TEXT DEFAULT ''"
    )

    con.commit()
    con.close()


init_db()


# =========================================================
# PYDANTIC MODELS
# =========================================================

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"


class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    description: str


class ApplicationCreate(BaseModel):
    job_id: int


class InterviewCreate(BaseModel):
    application_id: int
    interview_date: str
    interviewer: str
    mode: str = "Online"
    meeting_link: str = ""
    notes: str = ""


# =========================================================
# CURRENT USER
# =========================================================

def current_user(
    token: str = Depends(oauth2)
):
    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        con = db()

        user = con.execute(
            "SELECT * FROM users WHERE id=?",
            (int(user_id),)
        ).fetchone()

        con.close()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return dict(user)

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "PlacementHub Backend API is running",
        "health": "/api/health"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "placement-interview-management"
    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/register")
def register(data: Register):

    role = data.role.lower().strip()
    email = data.email.lower().strip()
    name = data.name.strip()

    if role not in {
        "student",
        "recruiter",
        "admin"
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required"
        )

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 6 characters"
        )

    con = db()

    try:
        # Check existing email first.
        existing = con.execute(
            "SELECT id FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        # Hash password using bcrypt directly.
        hashed_password = bcrypt.hashpw(
            data.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cur = con.execute(
            """
            INSERT INTO users(
                name,
                email,
                password,
                role
            )
            VALUES(?,?,?,?)
            """,
            (
                name,
                email,
                hashed_password,
                role
            )
        )

        con.commit()

        return {
            "message": "Registration successful",
            "id": cur.lastrowid
        }

    except HTTPException:
        raise

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    except Exception as e:
        print("REGISTRATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )

    finally:
        con.close()


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login(
    form: OAuth2PasswordRequestForm = Depends()
):

    con = db()

    user = con.execute(
        "SELECT * FROM users WHERE email=?",
        (form.username.lower().strip(),)
    ).fetchone()

    con.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    try:
        password_valid = bcrypt.checkpw(
            form.password.encode("utf-8"),
            user["password"].encode("utf-8")
        )
    except Exception:
        password_valid = False

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "exp": datetime.utcnow() + timedelta(hours=8)
        },
        SECRET,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


# =========================================================
# USER PROFILE
# =========================================================

@app.get("/api/me")
def me(
    user=Depends(current_user)
):

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }


# =========================================================
# CREATE JOB
# =========================================================

@app.post("/api/jobs")
def create_job(
    data: JobCreate,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:
        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    con = db()

    try:
        cur = con.execute(
            """
            INSERT INTO jobs(
                title,
                company,
                location,
                description,
                posted_by
            )
            VALUES(?,?,?,?,?)
            """,
            (
                data.title.strip(),
                data.company.strip(),
                data.location.strip(),
                data.description.strip(),
                user["id"]
            )
        )

        con.commit()

        return {
            "message": "Job created",
            "id": cur.lastrowid
        }

    finally:
        con.close()


# =========================================================
# GET JOBS
# =========================================================

@app.get("/api/jobs")
def jobs(
    user=Depends(current_user)
):

    con = db()

    try:
        rows = con.execute(
            """
            SELECT *
            FROM jobs
            ORDER BY id DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        con.close()


# =========================================================
# APPLY FOR JOB
# =========================================================

@app.post("/api/applications")
def apply(
    data: ApplicationCreate,
    user=Depends(current_user)
):

    if user["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Student access required"
        )

    con = db()

    try:
        job = con.execute(
            "SELECT id FROM jobs WHERE id=?",
            (data.job_id,)
        ).fetchone()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )

        existing = con.execute(
            """
            SELECT id
            FROM applications
            WHERE job_id=? AND student_id=?
            """,
            (
                data.job_id,
                user["id"]
            )
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="You have already applied for this job"
            )

        cur = con.execute(
            """
            INSERT INTO applications(
                job_id,
                student_id
            )
            VALUES(?,?)
            """,
            (
                data.job_id,
                user["id"]
            )
        )

        con.commit()

        return {
            "message": "Application submitted",
            "id": cur.lastrowid
        }

    finally:
        con.close()


# =========================================================
# GET APPLICATIONS
# =========================================================

@app.get("/api/applications")
def applications(
    user=Depends(current_user)
):

    con = db()

    try:
        if user["role"] == "student":

            rows = con.execute(
                """
                SELECT
                    a.*,
                    j.title,
                    j.company,
                    u.name AS student_name
                FROM applications a
                JOIN jobs j
                    ON a.job_id = j.id
                JOIN users u
                    ON a.student_id = u.id
                WHERE a.student_id=?
                ORDER BY a.id DESC
                """,
                (user["id"],)
            ).fetchall()

        else:

            rows = con.execute(
                """
                SELECT
                    a.*,
                    j.title,
                    j.company,
                    u.name AS student_name
                FROM applications a
                JOIN jobs j
                    ON a.job_id = j.id
                JOIN users u
                    ON a.student_id = u.id
                ORDER BY a.id DESC
                """
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        con.close()


# =========================================================
# UPDATE APPLICATION STATUS
# =========================================================

@app.patch("/api/applications/{application_id}/status")
def update_status(
    application_id: int,
    status: str,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:
        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    allowed = {
        "Applied",
        "Shortlisted",
        "Rejected",
        "Selected"
    }

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    con = db()

    try:
        result = con.execute(
            """
            UPDATE applications
            SET status=?
            WHERE id=?
            """,
            (
                status,
                application_id
            )
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Application not found"
            )

        con.commit()

        return {
            "message": "Status updated"
        }

    finally:
        con.close()


# =========================================================
# CREATE INTERVIEW
# =========================================================

@app.post("/api/interviews")
def create_interview(
    data: InterviewCreate,
    user=Depends(current_user)
):

    if user["role"] not in {
        "recruiter",
        "admin"
    }:
        raise HTTPException(
            status_code=403,
            detail="Recruiter/admin access required"
        )

    con = db()

    try:
        application = con.execute(
            """
            SELECT id
            FROM applications
            WHERE id=?
            """,
            (data.application_id,)
        ).fetchone()

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found"
            )

        cur = con.execute(
            """
            INSERT INTO interviews(
                application_id,
                interview_date,
                interviewer,
                mode,
                meeting_link,
                notes
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                data.application_id,
                data.interview_date,
                data.interviewer,
                data.mode,
                data.meeting_link,
                data.notes
            )
        )

        con.execute(
            """
            UPDATE applications
            SET status='Shortlisted'
            WHERE id=?
            """,
            (data.application_id,)
        )

        con.commit()

        return {
            "message": "Interview scheduled",
            "id": cur.lastrowid
        }

    finally:
        con.close()


# =========================================================
# GET INTERVIEWS
# =========================================================

@app.get("/api/interviews")
def interviews(
    user=Depends(current_user)
):

    con = db()

    try:
        rows = con.execute(
            """
            SELECT
                i.*,
                a.status,
                j.title,
                j.company,
                u.name AS student_name
            FROM interviews i
            JOIN applications a
                ON i.application_id = a.id
            JOIN jobs j
                ON a.job_id = j.id
            JOIN users u
                ON a.student_id = u.id
            ORDER BY i.interview_date
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        con.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/api/dashboard")
def dashboard(
    user=Depends(current_user)
):

    con = db()

    try:
        stats = {
            "jobs": con.execute(
                "SELECT COUNT(*) FROM jobs"
            ).fetchone()[0],

            "applications": con.execute(
                "SELECT COUNT(*) FROM applications"
            ).fetchone()[0],

            "interviews": con.execute(
                "SELECT COUNT(*) FROM interviews"
            ).fetchone()[0],

            "selected": con.execute(
                """
                SELECT COUNT(*)
                FROM applications
                WHERE status='Selected'
                """
            ).fetchone()[0]
        }

        return stats

    finally:
        con.close()

